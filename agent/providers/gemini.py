import os
import json
import time # Added time for rate-limiting
import google.generativeai as genai
from dotenv import load_dotenv
from agent.providers.base import AIProvider

class GeminiProvider(AIProvider):
    """
    AIProvider implementation using Google's Gemini model.
    """
    def __init__(self, model_name="gemini-1.5-flash-latest"): # Or "gemini-pro" / "gemini-1.0-pro"
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.env'))
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables. Ensure it's set in config/.env")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        self.generation_config = genai.types.GenerationConfig(
            # Only one candidate for now
            candidate_count=1,
            # We want JSON output
            response_mime_type="application/json",
            temperature=0.2, # Lower temperature for more deterministic actions
        )


    def get_next_action(self, objective: str, history: list[dict], dom: list[dict]) -> dict:
        """
        Gets the next action from the Gemini model.
        """
        prompt = self._construct_prompt(objective, history, dom)

        print("\\n----- Gemini Prompt for get_next_action -----")
        print(prompt)
        print("----- End Gemini Prompt for get_next_action -----\\n")

        try:
            print("Waiting for 5 seconds before calling Gemini API (get_next_action) to avoid rate limits...")
            time.sleep(5)
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )

            print("\\n----- Gemini Raw Response (get_next_action) -----")
            print(response.text) # Accessing .text directly as response_mime_type is application/json
            print("----- End Gemini Raw Response -----\\n")

            if response.parts:
                # Assuming the response is valid JSON as requested
                action_json_str = response.text
                action_data = json.loads(action_json_str)

                # Basic validation of the returned structure
                if "action" not in action_data:
                    print("Error: 'action' field missing in Gemini response.")
                    return {"action": "fail", "reasoning": "AI response missing 'action' field."}

                # Further validation can be added here based on action type
                # e.g., if action is 'click', 'selector' should be present.

                return action_data
            else:
                # Handle cases where response might be blocked or empty
                print("Warning: Gemini response has no parts or might be blocked.")
                # You might want to inspect response.prompt_feedback here for safety ratings
                if response.prompt_feedback:
                    print(f"Prompt Feedback: {response.prompt_feedback}")
                return {"action": "fail", "reasoning": "AI response was empty or blocked."}

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from Gemini response: {e}")
            print(f"Raw response was: {response.text if 'response' in locals() and hasattr(response, 'text') else 'N/A'}")
            return {"action": "fail", "reasoning": f"Invalid JSON response from AI: {e}"}
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return {"action": "fail", "reasoning": f"API call failed: {e}"}

    def _construct_prompt(self, objective: str, history: list[dict], dom: list[dict]) -> str:
        """
        Constructs the detailed prompt for the Gemini model.
        """
        # Prune DOM to reduce token count if necessary, prioritize elements with clearer selectors or more info
        # For now, we send the whole DOM as received.
        # A more sophisticated approach might involve summarizing or filtering the DOM further.

        dom_summary_for_prompt = []
        for el in dom:
            # Create a more compact representation for the prompt
            summary = {
                "tag": el.get("tag"),
                "selector": el.get("selector"), # This is our generated one
                "attributes": {k: v for k, v in el.get("attributes", {}).items() if k in ['id', 'name', 'aria-label', 'placeholder', 'role', 'type', 'href', 'data-testid']},
                "text": el.get("text_content", "")[:100] # Truncate text
            }
            # Only include selector if it exists
            if not summary["selector"]:
                del summary["selector"] # Let the AI choose based on other attributes if no good selector

            dom_summary_for_prompt.append(summary)


        prompt = f"""You are an AI agent controlling a web browser to achieve a specific objective.
Your task is to decide the next action to take based on the current state of the webpage and the history of actions taken so far.

Objective: {objective}

Current Simplified DOM (interactive elements only):
{json.dumps(dom_summary_for_prompt, indent=2)}

History of actions taken so far (last 5 actions):
{json.dumps(history[-5:], indent=2) if history else "No actions taken yet."}

Based on the objective, the DOM, and the history, what is the next single action to perform?
Your response MUST be a JSON object with the following structure:
{{
  "action": "action_type",      // one of: "click", "type", "select", "finish", "fail"
  "selector": "CSS_selector",   // required for "click", "type", "select". Use the 'selector' field from DOM if available and suitable. Otherwise, construct a robust CSS selector.
  "text": "text_to_type",       // required for "type"
  "value": "value_to_select",   // required for "select" (usually the 'value' attribute of an <option>)
  "reasoning": "your_reasoning" // brief explanation of why you chose this action
}}

Guidelines for choosing selectors:
- Prefer selectors provided in the DOM elements if they are unique and stable (e.g., `#{el['attributes'].get('id')}`, `[name='{el['attributes'].get('name')}']`, `[data-testid='...']`).
- If no good pre-defined selector, construct one using tag, attributes, and text. For example: `button:has-text('Submit')`, `input[name='email']`, `a[href*='product']`.
- Be specific to avoid ambiguity.

Available actions:
- "click": Clicks an element. Requires "selector".
- "type": Types text into an input field or textarea. Requires "selector" and "text".
- "select": Selects an option from a <select> dropdown. Requires "selector" and "value" (the option's value attribute).
- "finish": Use this action if you believe the objective has been successfully completed.
- "fail": Use this action if you are stuck, cannot find a way to proceed, or an error has occurred that prevents completion.

Consider the objective carefully. If the current page seems to satisfy the objective, use "finish".
If you need to interact with an element, ensure it is present in the DOM and choose the best selector.
If you are typing, ensure the element is an input or textarea.
If you are selecting, ensure the element is a select and the value is one of its options.

Example of choosing a selector for a button with text "Login" and id "login-btn":
If DOM has: {{ "tag": "button", "selector": "#login-btn", "attributes": {{ "id": "login-btn" }}, "text": "Login" }}
Your action: {{ "action": "click", "selector": "#login-btn", "reasoning": "Clicking the login button with id login-btn." }}

Example for typing into a search bar:
If DOM has: {{ "tag": "input", "attributes": {{ "name": "q", "aria-label": "Search" }}, "text": "" }}
Your action: {{ "action": "type", "selector": "input[name='q']", "text": "my search query", "reasoning": "Typing search query into the search bar." }}

Now, provide the next action JSON object:
"""
        return prompt

    def get_test_plan(self, objective: str, start_url: str, dom: list[dict]) -> list[str]:
        """
        Generates a high-level test plan using the Gemini model.
        """
        prompt = self._construct_plan_prompt(objective, start_url, dom)

        print("\\n----- Gemini Prompt for get_test_plan -----")
        print(prompt)
        print("----- End Gemini Prompt for get_test_plan -----\\n")

        try:
            print("Waiting for 5 seconds before calling Gemini API (get_test_plan) to avoid rate limits...")
            time.sleep(5)
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config # Expecting JSON array
            )

            print("\\n----- Gemini Raw Response (get_test_plan) -----")
            print(response.text)
            print("----- End Gemini Raw Response (get_test_plan) -----\\n")

            if response.parts:
                plan_json_str = response.text
                try:
                    plan_array = json.loads(plan_json_str)
                    if not isinstance(plan_array, list) or not all(isinstance(step, str) for step in plan_array):
                        print("Error: Gemini response for plan is not a JSON array of strings.")
                        return ["Error: AI response for plan was not a JSON array of strings."]
                    return plan_array
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON plan from Gemini response: {e}")
                    return [f"Error: Invalid JSON plan from AI: {e}"]
            else:
                print("Warning: Gemini response for plan has no parts or might be blocked.")
                if response.prompt_feedback:
                    print(f"Prompt Feedback: {response.prompt_feedback}")
                return ["Error: AI response for plan was empty or blocked."]

        except Exception as e:
            print(f"Error calling Gemini API for get_test_plan: {e}")
            return [f"Error: API call for plan failed: {e}"]

    def _construct_plan_prompt(self, objective: str, start_url: str, dom: list[dict]) -> str:
        """
        Constructs the prompt for the Gemini model to generate a test plan.
        """
        dom_summary_for_prompt = []
        for el in dom:
            summary = {
                "tag": el.get("tag"),
                "selector": el.get("selector"),
                "attributes": {k: v for k, v in el.get("attributes", {}).items() if k in ['id', 'name', 'aria-label', 'placeholder', 'role', 'type', 'href', 'data-testid']},
                "text": el.get("text_content", "")[:100]
            }
            if not summary["selector"]:
                del summary["selector"]
            dom_summary_for_prompt.append(summary)

        prompt = f"""You are a QA planning agent.
Your task is to analyze a high-level objective, a starting URL, and the initial state of the webpage's DOM (simplified to interactive elements) to create a test plan.
The test plan should be a sequence of high-level steps to achieve the objective.
Return these steps as a JSON array of strings.

Objective: {objective}
Start URL: {start_url}

Initial Simplified DOM (interactive elements only):
{json.dumps(dom_summary_for_prompt, indent=2)}

Based on the objective and the initial page state, break down the task into a series of high-level steps.
Return these steps as a JSON array of strings.

Example:
If the objective is "Login to the website with username 'testuser' and password 'securepass', then verify 'Welcome' is visible."
A possible plan would be:
["Enter 'testuser' into the username field", "Enter 'securepass' into the password field", "Click the 'Login' button", "Verify the text 'Welcome' is visible on the page"]

Now, provide the JSON array of strings for the given objective and DOM:
"""
        return prompt

if __name__ == '__main__':
    # This is a mock test, it won't actually run the browser.
    # It's for testing the prompt construction and API call to Gemini.
    # Note: These tests will take longer due to the 5-second delays.
    print("Testing GeminiProvider (expect delays due to rate limit sleeps)...")

    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.env')
    if not os.path.exists(config_path) or not os.getenv("GOOGLE_API_KEY", None):
        print(f"Skipping GeminiProvider direct API test as GOOGLE_API_KEY is not available or {config_path} is missing.")
        if not os.path.exists(config_path):
            print(f"Creating a dummy {config_path} for structure.")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                f.write('GOOGLE_API_KEY="YOUR_KEY_HERE_FOR_TESTING"\n')
                f.write('OPENAI_API_KEY="YOUR_KEY_HERE_FOR_TESTING"\n')
    else:
        try:
            provider = GeminiProvider()

            # --- Test get_test_plan ---
            print("\\n--- Testing get_test_plan ---")
            plan_objective = "Log into the website with username 'testuser' and password 'securepass', then check for 'Welcome' message."
            plan_start_url = "https://example.com/login"
            plan_mock_dom = [
                {"tag": "input", "selector": "input[name='username']", "attributes": {"name": "username", "type": "text"}, "text_content": ""},
                {"tag": "input", "selector": "input[name='password']", "attributes": {"name": "password", "type": "password"}, "text_content": ""},
                {"tag": "button", "selector": "button[type='submit']", "attributes": {"type": "submit"}, "text_content": "Login"}
            ]

            test_plan = provider.get_test_plan(plan_objective, plan_start_url, plan_mock_dom)
            print("\\nTest Plan from Gemini:")
            print(json.dumps(test_plan, indent=2))
            assert isinstance(test_plan, list), "Test plan should be a list."
            if test_plan: # If not empty or error
                 assert all(isinstance(step, str) for step in test_plan), "All steps in the plan should be strings."
                 if not any("Error:" in step for step in test_plan):
                    assert len(test_plan) > 1, "Expected a plan with multiple steps for the given objective."

            # --- Test get_next_action ---
            print("\\n--- Testing get_next_action ---")
            action_objective = "Enter 'testuser' into the username field" # Example of a step from a plan
            action_history = [
                {"action": "navigate", "url": "https://example.com/login", "status": "success"},
                {"action": "plan_generation", "plan": ["Step 1", "Step 2"], "status": "success"}
            ]
            action_mock_dom = plan_mock_dom # Use the same DOM as for planning for this example step

            next_action = provider.get_next_action(action_objective, action_history, action_mock_dom)
            print("\\nNext Action from Gemini:")
            print(json.dumps(next_action, indent=2))
            assert isinstance(next_action, dict), "Next action should be a dictionary."
            assert "action" in next_action, "Next action must contain an 'action' field."
            if next_action.get("action") not in ["fail", "finish"]:
                assert "selector" in next_action, "Action requires a selector."


            # --- Test get_next_action for a "finish" type step (conceptually) ---
            # This tests if the AI can correctly identify a "finish" based on a step objective.
            print("\\n--- Testing get_next_action (for a 'finish' step) ---")
            finish_step_objective = "Verify the text 'Welcome' is visible on the page"
            finish_mock_dom = [
                {"tag": "h1", "text_content": "Welcome, testuser!", "attributes":{}},
                {"tag": "p", "text_content": "You have successfully logged in.", "attributes":{}}
            ]
            finish_history = [
                 {"action": "type", "selector": "input[name='username']", "text": "testuser", "status": "success"},
                 {"action": "type", "selector": "input[name='password']", "text": "securepass", "status": "success"},
                 {"action": "click", "selector": "button[type='submit']", "status": "success"}
            ]

            finish_action = provider.get_next_action(finish_step_objective, finish_history, finish_mock_dom)
            print("\\nNext Action for 'finish' step from Gemini:")
            print(json.dumps(finish_action, indent=2))
            assert isinstance(finish_action, dict)
            # For a verification step, the AI might still try to look for things,
            # or it might correctly say "finish" if the objective implies verification is the end.
            # The prompt for get_next_action guides it to 'finish' if the *step_objective* is met.
            assert finish_action.get("action") == "finish", "Expected AI to 'finish' the verification step if DOM confirms it."

        except ValueError as ve:
            print(f"Skipping GeminiProvider test due to configuration error: {ve}")
        except Exception as e:
            print(f"An error occurred during GeminiProvider test: {e}")

    print("GeminiProvider tests (including get_test_plan) completed.")
