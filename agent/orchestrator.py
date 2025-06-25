import time
from agent.browser.controller import BrowserController
from agent.providers.base import AIProvider

class Orchestrator:
    def __init__(self, provider: AIProvider, max_attempts=10):
        self.ai_provider = provider
        self.browser_controller = BrowserController()
        self.max_attempts = max_attempts

    def run_test(self, objective: str, start_url: str) -> tuple[bool, list[dict]]:
        """
        Runs the AI-driven test loop.

        Args:
            objective: The high-level goal for the agent.
            start_url: The initial URL to navigate to.

        Returns:
            A tuple containing:
                - bool: True if the objective was achieved ("finish"), False otherwise.
                - list[dict]: The history of actions taken.
        """
        history = []

        print(f"Navigating to start URL: {start_url}")
        self.browser_controller.navigate(start_url)
        history.append({"action": "navigate", "url": start_url, "status": "success", "reasoning": "Initial navigation"})

        for attempt in range(self.max_attempts):
            print(f"\\n--- Attempt {attempt + 1}/{self.max_attempts} ---")

            # 1. Observe
            print("Observing page DOM...")
            try:
                current_dom = self.browser_controller.get_simplified_dom()
                if not current_dom:
                    print("Warning: Current DOM is empty or could not be fetched.")
                    # Potentially add a small delay and retry DOM fetching once
                    time.sleep(1)
                    current_dom = self.browser_controller.get_simplified_dom()
                    if not current_dom:
                         print("Error: DOM is still empty after retry. Failing attempt.")
                         history.append({"action": "error", "message": "Failed to retrieve DOM.", "status": "error"})
                         # Consider if this should be a hard fail or if AI should try to proceed
                         # For now, let AI decide based on empty DOM if it gets there
            except Exception as e:
                print(f"Error during DOM observation: {e}")
                history.append({"action": "error", "message": f"DOM observation failed: {e}", "status": "error"})
                # Let AI try to handle this, or fail if it can't
                current_dom = []


            # 2. Plan
            print("Asking AI for next action...")
            ai_action = self.ai_provider.get_next_action(objective, history, current_dom)

            print(f"AI suggested action: {ai_action}")

            action_type = ai_action.get("action")
            action_selector = ai_action.get("selector")
            action_text = ai_action.get("text")
            action_value = ai_action.get("value")
            action_reasoning = ai_action.get("reasoning", "No reasoning provided by AI.")

            current_action_record = {
                "action": action_type,
                "selector": action_selector,
                "text": action_text,
                "value": action_value,
                "reasoning": action_reasoning,
                "status": "pending"
            }

            # 3. Act
            if action_type == "click":
                if not action_selector:
                    print("Error: AI action 'click' missing 'selector'.")
                    current_action_record["status"] = "error"
                    current_action_record["error_message"] = "Missing selector for click action."
                else:
                    try:
                        print(f"Attempting to click: {action_selector}")
                        self.browser_controller.click_element(action_selector)
                        current_action_record["status"] = "success"
                    except Exception as e:
                        print(f"Error clicking element {action_selector}: {e}")
                        current_action_record["status"] = "error"
                        current_action_record["error_message"] = str(e)

            elif action_type == "type":
                if not action_selector or action_text is None: # text can be empty string
                    print("Error: AI action 'type' missing 'selector' or 'text'.")
                    current_action_record["status"] = "error"
                    current_action_record["error_message"] = "Missing selector or text for type action."
                else:
                    try:
                        print(f"Attempting to type '{action_text}' into: {action_selector}")
                        self.browser_controller.type_in_element(action_selector, action_text)
                        current_action_record["status"] = "success"
                    except Exception as e:
                        print(f"Error typing into element {action_selector}: {e}")
                        current_action_record["status"] = "error"
                        current_action_record["error_message"] = str(e)

            elif action_type == "select":
                if not action_selector or not action_value:
                    print("Error: AI action 'select' missing 'selector' or 'value'.")
                    current_action_record["status"] = "error"
                    current_action_record["error_message"] = "Missing selector or value for select action."
                else:
                    try:
                        print(f"Attempting to select option '{action_value}' in: {action_selector}")
                        self.browser_controller.select_option(action_selector, action_value)
                        current_action_record["status"] = "success"
                    except Exception as e:
                        print(f"Error selecting option in {action_selector}: {e}")
                        current_action_record["status"] = "error"
                        current_action_record["error_message"] = str(e)

            elif action_type == "finish":
                print(f"Objective achieved: {objective}. Reason: {action_reasoning}")
                current_action_record["status"] = "success"
                history.append(current_action_record)
                self.browser_controller.shutdown()
                return True, history

            elif action_type == "fail":
                print(f"AI indicated failure to achieve objective. Reason: {action_reasoning}")
                current_action_record["status"] = "failed_by_ai"
                history.append(current_action_record)
                self.browser_controller.shutdown()
                return False, history

            else:
                print(f"Error: Unknown action type '{action_type}' received from AI.")
                current_action_record["status"] = "error"
                current_action_record["error_message"] = f"Unknown AI action type: {action_type}"

            history.append(current_action_record)

            # Small delay to allow page to update after an action, and to make it watchable
            time.sleep(2) # TODO: Make configurable or smarter (e.g., wait for specific conditions)

            if current_action_record["status"] == "error" or current_action_record["status"] == "failed_by_ai":
                # If an action results in an error, or AI explicitly fails, consider if we should stop early.
                # For now, we'll let it run max_attempts unless AI says "fail" or "finish".
                # If an operational error occurs (e.g. can't click), the next DOM might help AI recover.
                print(f"Action resulted in status: {current_action_record['status']}. Continuing if attempts remain.")


        print(f"Max attempts ({self.max_attempts}) reached. Objective may not have been fully achieved.")
        self.browser_controller.shutdown()
        return False, history

if __name__ == '__main__':
    # This is a conceptual test. It requires a mock AIProvider.
    class MockAIProvider(AIProvider):
        def __init__(self):
            self.call_count = 0
        def get_next_action(self, objective: str, history: list, dom: list) -> dict:
            self.call_count += 1
            if self.call_count == 1:
                # Simulate finding a search bar and typing
                return {"action": "type", "selector": "input[name='search']", "text": "hello world", "reasoning": "Typing into search bar"}
            elif self.call_count == 2:
                # Simulate clicking a search button
                return {"action": "click", "selector": "button[id='search-btn']", "reasoning": "Clicking search button"}
            elif self.call_count == 3:
                 # Simulate objective met
                return {"action": "finish", "reasoning": "Search results page loaded, objective met."}
            return {"action": "fail", "reasoning": "Mock AI stuck."}

    print("Testing Orchestrator with MockAIProvider...")

    # We need a config/.env for BrowserController to init Playwright, even if AI is mocked.
    # And GeminiProvider (even if not directly used here) needs it for its __init__.
    # Ensure config/.env exists.
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    env_file = os.path.join(config_dir, '.env')
    os.makedirs(config_dir, exist_ok=True)
    if not os.path.exists(env_file):
        print(f"Creating dummy {env_file} for test.")
        with open(env_file, 'w') as f:
            f.write('GOOGLE_API_KEY="YOUR_KEY_HERE_FOR_TESTING"\n')
            f.write('OPENAI_API_KEY="YOUR_KEY_HERE_FOR_TESTING"\n')

    mock_provider = MockAIProvider()
    orchestrator = Orchestrator(provider=mock_provider, max_attempts=5)

    # For this test to run without actual browser errors, we'd need to either:
    # 1. Mock BrowserController methods heavily.
    # 2. Run against a known simple local HTML page or a very stable simple website.
    # For now, this will likely print errors from BrowserController as it tries to interact
    # with a non-existent page or elements if not navigated to a real URL.
    # Let's use a public, simple page for testing.
    # test_objective = "Search for 'hello world' on a search engine and then finish."
    # test_start_url = "https://www.google.com" # Replace with a more stable test page if needed

    # Simplified test that doesn't rely on external sites for basic orchestration flow.
    # The BrowserController will still launch a browser but actions will likely fail on about:blank.
    # This tests the loop mechanics more than browser interaction.
    test_objective = "Perform a few mock actions and finish."
    test_start_url = "about:blank" # A blank page, actions will fail but loop should run

    print(f"Starting orchestrator test with objective: '{test_objective}' and URL: '{test_start_url}'")

    success, history_log = orchestrator.run_test(test_objective, test_start_url)

    print(f"\\nOrchestrator test finished. Success: {success}")
    print("History Log:")
    for i, entry in enumerate(history_log):
        print(f"{i+1}. {entry}")

    assert mock_provider.call_count <= 3 + 1 # navigate + 3 AI calls (type, click, finish)
    if success:
        assert history_log[-1]["action"] == "finish"
    else:
        # If it didn't "finish", it might be due to max_attempts or "fail" from AI
        assert history_log[-1]["action"] == "fail" or len(history_log) >= orchestrator.max_attempts +1 # +1 for initial navigate
    print("Orchestrator test with MockAIProvider completed.")
