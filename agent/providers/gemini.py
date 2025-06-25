import os
import json
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

        print("\\n----- Gemini Prompt -----")
        print(prompt)
        print("----- End Gemini Prompt -----\\n")

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )

            print("\\n----- Gemini Raw Response -----")
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

if __name__ == '__main__':
    # This is a mock test, it won't actually run the browser.
    # It's for testing the prompt construction and API call.
    print("Testing GeminiProvider...")

    # Ensure config/.env exists with a GOOGLE_API_KEY for this test to run fully
    if not os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.env')) or not os.getenv("GOOGLE_API_KEY", None):
        print("Skipping GeminiProvider direct test as GOOGLE_API_KEY is not available or config/.env is missing.")
        # Create a dummy .env for subsequent steps if it doesn't exist
        if not os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.env')):
            print("Creating a dummy config/.env file for structure.")
            os.makedirs(os.path.join(os.path.dirname(__file__), '..', '..', 'config'), exist_ok=True)
            with open(os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.env'), 'w') as f:
                f.write('GOOGLE_API_KEY="YOUR_KEY_HERE_FOR_TESTING"\n')
                f.write('OPENAI_API_KEY="YOUR_KEY_HERE_FOR_TESTING"\n')

    else:
        try:
            provider = GeminiProvider()

            mock_objective = "Find the contact page and click on the email address."
            mock_history = [
                {"action": "navigate", "url": "https://example.com", "status": "success"},
                {"action": "click", "selector": "a[href='/about']", "reasoning": "Navigating to about page", "status": "success"}
            ]
            mock_dom = [
                {"tag": "a", "selector": "#contact-link", "attributes": {"id": "contact-link", "href": "/contact"}, "text_content": "Contact Us", "is_visible": True, "is_enabled": True},
                {"tag": "input", "selector": "input[name='search']", "attributes": {"name": "search", "type": "search"}, "text_content": "", "is_visible": True, "is_enabled": True},
                {"tag": "button", "text_content": "Submit", "is_visible": True, "is_enabled": True, "attributes": {}}
            ]

            next_action = provider.get_next_action(mock_objective, mock_history, mock_dom)
            print("\\nNext Action from Gemini:")
            print(json.dumps(next_action, indent=2))

            # Test a "finish" scenario (conceptually)
            mock_objective_finish = "You are on the login page. The user wants to log in."
            mock_dom_login = [
                 {"tag": "input", "selector": "input[name='username']", "attributes": {"name": "username"}, "text_content": "", "is_visible": True, "is_enabled": True},
                 {"tag": "input", "selector": "input[name='password']", "attributes": {"name": "password", "type": "password"}, "text_content": "", "is_visible": True, "is_enabled": True},
                 {"tag": "button", "selector": "button[type='submit']", "attributes": {"type": "submit"}, "text_content": "Log In", "is_visible": True, "is_enabled": True}
            ]
            mock_history_login_attempt = [
                {"action": "type", "selector": "input[name='username']", "text": "testuser", "status": "success"},
                {"action": "type", "selector": "input[name='password']", "text": "password", "status": "success"},
                {"action": "click", "selector": "button[type='submit']", "status": "success", "reasoning": "Attempting login"}
            ]
            # Now imagine the objective is "Successfully logged in and reached dashboard"
            # And the DOM shows dashboard elements
            mock_objective_dashboard = "Successfully logged in and view dashboard"
            mock_dom_dashboard = [
                {"tag": "h1", "text_content": "Welcome to your Dashboard!", "is_visible": True, "is_enabled": True, "attributes":{}},
                {"tag": "a", "selector": "a[href='/logout']", "attributes": {"href": "/logout"}, "text_content": "Logout", "is_visible": True, "is_enabled": True}
            ]

            print("\\nTesting 'finish' scenario conceptually:")
            next_action_finish = provider.get_next_action(mock_objective_dashboard, mock_history_login_attempt, mock_dom_dashboard)
            print("Next Action for 'finish' scenario:")
            print(json.dumps(next_action_finish, indent=2))


        except ValueError as ve:
            print(f"Skipping GeminiProvider test due to configuration error: {ve}")
        except Exception as e:
            print(f"An error occurred during GeminiProvider test: {e}")

    print("GeminiProvider structure created.")
