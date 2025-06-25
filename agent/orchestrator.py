import time
import json # For potential plan logging, though AI provider returns list of strings
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
        overall_objective = objective # Store the original high-level objective

        print(f"Navigating to start URL: {start_url}")
        self.browser_controller.navigate(start_url)
        history.append({"action": "navigate", "url": start_url, "status": "success", "reasoning": "Initial navigation"})

        # --- Phase A: Planning ---
        print("\\n--- Phase A: Planning ---")
        try:
            initial_dom = self.browser_controller.get_simplified_dom()
            if not initial_dom: # Retry once if DOM is empty
                time.sleep(1)
                initial_dom = self.browser_controller.get_simplified_dom()
        except Exception as e:
            print(f"Error getting initial DOM for planning: {e}")
            history.append({"action": "error", "message": f"Failed to get initial DOM: {e}", "status": "error", "phase": "planning"})
            self.browser_controller.shutdown()
            return False, history

        print(f"Asking AI for test plan for objective: {overall_objective}")
        test_plan = self.ai_provider.get_test_plan(overall_objective, start_url, initial_dom)

        if not test_plan or not isinstance(test_plan, list) or not all(isinstance(step, str) for step in test_plan) or "Error:" in test_plan[0]:
            print(f"Failed to generate a valid test plan. Plan received: {test_plan}")
            history.append({"action": "plan_generation", "plan": test_plan, "status": "error", "reasoning": "Failed to get valid plan from AI."})
            self.browser_controller.shutdown()
            return False, history

        print(f"AI generated test plan: {test_plan}")
        history.append({"action": "plan_generation", "plan": test_plan, "status": "success", "reasoning": "AI Generated Test Plan"})

        # --- Phase B: Execution ---
        print("\\n--- Phase B: Execution ---")
        for i, step_objective in enumerate(test_plan):
            print(f"\\n--- Executing Step {i + 1}/{len(test_plan)}: {step_objective} ---")
            step_achieved = False
            for attempt in range(self.max_attempts):
                print(f"--- Step Attempt {attempt + 1}/{self.max_attempts} ---")

                # 1. Observe
                print("Observing page DOM for step...")
                try:
                    current_dom = self.browser_controller.get_simplified_dom()
                    if not current_dom:
                        print("Warning: Current DOM is empty. Retrying once.")
                        time.sleep(1)
                        current_dom = self.browser_controller.get_simplified_dom()
                        if not current_dom:
                            print("Error: DOM is still empty after retry for step.")
                            # Log this attempt's failure but don't immediately fail the step, let AI try
                            history.append({"action": "observe_dom", "step": step_objective, "attempt": attempt + 1, "status": "error", "message": "DOM empty"})
                            # current_dom remains empty, AI might decide to 'fail'
                except Exception as e:
                    print(f"Error during DOM observation for step: {e}")
                    history.append({"action": "observe_dom", "step": step_objective, "attempt": attempt + 1, "status": "error", "message": f"DOM observation failed: {e}"})
                    current_dom = [] # Let AI try to handle this

                # 2. Plan (for the current step)
                print(f"Asking AI for next action for step: '{step_objective}'")
                # Pass only relevant recent history for the current step? Or full history?
                # For now, passing full history. Can be optimized later.
                ai_action = self.ai_provider.get_next_action(step_objective, history, current_dom)
                print(f"AI suggested action for step: {ai_action}")

                action_type = ai_action.get("action")
                action_selector = ai_action.get("selector")
                action_text = ai_action.get("text")
                action_value = ai_action.get("value")
                action_reasoning = ai_action.get("reasoning", "No reasoning provided by AI.")

                current_action_record = {
                    "step_objective": step_objective,
                    "action": action_type,
                    "selector": action_selector,
                    "text": action_text,
                    "value": action_value,
                    "reasoning": action_reasoning,
                    "status": "pending",
                    "attempt": attempt + 1
                }

                # 3. Act
                action_failed_or_unknown = False
                if action_type == "click":
                    if not action_selector:
                        print("Error: AI action 'click' missing 'selector'.")
                        current_action_record["status"] = "error"
                        current_action_record["error_message"] = "Missing selector for click action."
                        action_failed_or_unknown = True
                    else:
                        try:
                            print(f"Attempting to click: {action_selector}")
                            self.browser_controller.click_element(action_selector)
                            current_action_record["status"] = "success"
                        except Exception as e:
                            print(f"Error clicking element {action_selector}: {e}")
                            current_action_record["status"] = "error"
                            current_action_record["error_message"] = str(e)
                            action_failed_or_unknown = True

                elif action_type == "type":
                    if not action_selector or action_text is None:
                        print("Error: AI action 'type' missing 'selector' or 'text'.")
                        current_action_record["status"] = "error"
                        current_action_record["error_message"] = "Missing selector or text for type action."
                        action_failed_or_unknown = True
                    else:
                        try:
                            print(f"Attempting to type '{action_text}' into: {action_selector}")
                            self.browser_controller.type_in_element(action_selector, action_text)
                            current_action_record["status"] = "success"
                        except Exception as e:
                            print(f"Error typing into element {action_selector}: {e}")
                            current_action_record["status"] = "error"
                            current_action_record["error_message"] = str(e)
                            action_failed_or_unknown = True

                elif action_type == "select":
                    if not action_selector or not action_value:
                        print("Error: AI action 'select' missing 'selector' or 'value'.")
                        current_action_record["status"] = "error"
                        current_action_record["error_message"] = "Missing selector or value for select action."
                        action_failed_or_unknown = True
                    else:
                        try:
                            print(f"Attempting to select option '{action_value}' in: {action_selector}")
                            self.browser_controller.select_option(action_selector, action_value)
                            current_action_record["status"] = "success"
                        except Exception as e:
                            print(f"Error selecting option in {action_selector}: {e}")
                            current_action_record["status"] = "error"
                            current_action_record["error_message"] = str(e)
                            action_failed_or_unknown = True

                elif action_type == "finish": # This "finish" now means the step is complete
                    print(f"AI indicated step '{step_objective}' achieved. Reason: {action_reasoning}")
                    current_action_record["status"] = "success"
                    step_achieved = True

                elif action_type == "fail": # This "fail" means AI cannot complete the current step
                    print(f"AI indicated failure to achieve step '{step_objective}'. Reason: {action_reasoning}")
                    current_action_record["status"] = "failed_by_ai_for_step"
                    action_failed_or_unknown = True # Treat as a failed attempt for the step

                else:
                    print(f"Error: Unknown action type '{action_type}' received from AI for step.")
                    current_action_record["status"] = "error"
                    current_action_record["error_message"] = f"Unknown AI action type: {action_type}"
                    action_failed_or_unknown = True

                history.append(current_action_record)

                if step_achieved:
                    print(f"Step '{step_objective}' successfully completed.")
                    break # Move to the next step in the plan

                if action_failed_or_unknown and current_action_record["status"] != "failed_by_ai_for_step":
                    print(f"Action for step '{step_objective}' resulted in status: {current_action_record['status']}. Continuing step attempts if any remain.")

                if current_action_record["status"] == "failed_by_ai_for_step":
                    print(f"AI failed step '{step_objective}'. This step will not be retried.")
                    break # AI has given up on this step, move to outer loop check

                # Small delay to allow page to update after an action
                time.sleep(1) # Reduced from 2, as main rate limit is on AI

            # After attempts for a step are exhausted or step is achieved/failed by AI
            if not step_achieved:
                print(f"Failed to achieve step '{step_objective}' after {self.max_attempts} attempts or AI failure.")
                history.append({"action": "step_execution_status", "step": step_objective, "status": "failed", "reasoning": f"Step not achieved after {self.max_attempts} attempts or AI indicated failure."})
                self.browser_controller.shutdown()
                return False, history # Entire test fails if one step fails

        # If all steps in the plan are completed
        print(f"All steps in the plan successfully executed. Overall objective '{overall_objective}' achieved.")
        history.append({"action": "overall_objective_status", "objective": overall_objective, "status": "success"})
        self.browser_controller.shutdown()
        return True, history

if __name__ == '__main__':
    # This is a conceptual test. It requires a mock AIProvider.
    import os # Ensure os is imported for the dummy .env creation
    class MockAIProvider(AIProvider):
        def __init__(self):
            self.get_plan_call_count = 0
            self.get_next_action_call_count = 0
            self.plan_steps_to_provide = []
            self.action_sequence = []
            self.action_idx = 0

        def get_test_plan(self, objective: str, start_url: str, dom: list[dict]) -> list[str]:
            self.get_plan_call_count += 1
            print(f"MockAIProvider.get_test_plan called with objective: '{objective}'")
            # Example plan, can be customized for different tests
            if not self.plan_steps_to_provide: # Default plan if not set
                self.plan_steps_to_provide = [
                    "Step 1: Type 'hello' into search",
                    "Step 2: Click search button",
                    "Step 3: Verify results"
                ]
            print(f"MockAIProvider providing plan: {self.plan_steps_to_provide}")
            return self.plan_steps_to_provide

        def get_next_action(self, objective: str, history: list, dom: list) -> dict:
            self.get_next_action_call_count += 1
            print(f"MockAIProvider.get_next_action called with step_objective: '{objective}' (action call {self.get_next_action_call_count})")

            if not self.action_sequence: # Default action sequence
                 # Default actions corresponding to the default plan
                default_actions = [
                    {"action": "type", "selector": "input[name='q']", "text": "hello", "reasoning": "Action for Step 1"},
                    {"action": "click", "selector": "button[type='submit']", "reasoning": "Action for Step 2"},
                    {"action": "finish", "reasoning": "Action for Step 3 - step finished"} # 'finish' here means step finished
                ]
                if self.get_next_action_call_count -1 < len(default_actions):
                    action_to_return = default_actions[self.get_next_action_call_count-1]
                    print(f"MockAIProvider returning action: {action_to_return}")
                    return action_to_return
                else:
                    # If called more times than actions available for steps, means something is wrong or test needs more actions
                    print("MockAIProvider: Ran out of predefined actions for steps, returning fail.")
                    return {"action": "fail", "reasoning": "Mock AI ran out of actions for steps."}

            # For customized action sequences
            if self.action_idx < len(self.action_sequence):
                action = self.action_sequence[self.action_idx]
                self.action_idx += 1
                print(f"MockAIProvider returning action: {action}")
                return action

            print("MockAIProvider: Ran out of custom actions, returning fail.")
            return {"action": "fail", "reasoning": "Mock AI stuck or ran out of custom actions."}

    print("Testing Orchestrator with new MockAIProvider...")

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
    # Simplified test that doesn't rely on external sites for basic orchestration flow.
    # The BrowserController will still launch a browser but actions will likely fail on about:blank,
    # which is fine for testing the orchestration logic itself.
    test_objective = "Complete a 3-step mock process."
    test_start_url = "about:blank"

    print(f"Starting orchestrator test with objective: '{test_objective}' and URL: '{test_start_url}'")

    # --- Test Case 1: Successful run with default mock plan & actions ---
    print("\\n--- Test Case 1: Successful Run ---")
    mock_provider_success = MockAIProvider()
    orchestrator_success = Orchestrator(provider=mock_provider_success, max_attempts=2)
    success, history_log = orchestrator_success.run_test(test_objective, test_start_url)

    print(f"Orchestrator test (success case) finished. Success: {success}")
    print("History Log (success case):")
    for i, entry in enumerate(history_log):
        print(f"{i+1}. {entry}")

    assert success, "Test case 1 should succeed"
    assert mock_provider_success.get_plan_call_count == 1, "get_test_plan should be called once"
    # Default plan has 3 steps, so get_next_action should be called 3 times.
    assert mock_provider_success.get_next_action_call_count == 3, "get_next_action should be called for each step in the default plan"
    assert history_log[-1]["action"] == "overall_objective_status" and history_log[-1]["status"] == "success"
    print("Orchestrator Test Case 1 (Successful Run) with MockAIProvider PASSED.")

    # --- Test Case 2: AI fails to generate a plan ---
    print("\\n--- Test Case 2: AI Fails to Generate Plan ---")
    mock_provider_plan_fail = MockAIProvider()
    mock_provider_plan_fail.plan_steps_to_provide = ["Error: Failed to generate plan from mock"] # Simulate AI error string
    orchestrator_plan_fail = Orchestrator(provider=mock_provider_plan_fail, max_attempts=2)
    success_plan_fail, history_plan_fail = orchestrator_plan_fail.run_test("Objective that leads to plan failure", test_start_url)

    print(f"Orchestrator test (plan failure case) finished. Success: {success_plan_fail}")
    assert not success_plan_fail, "Test case 2 (plan failure) should fail"
    assert mock_provider_plan_fail.get_plan_call_count == 1
    assert mock_provider_plan_fail.get_next_action_call_count == 0 # Should not proceed to actions
    assert history_plan_fail[-1]["action"] == "plan_generation" and history_plan_fail[-1]["status"] == "error"
    print("Orchestrator Test Case 2 (Plan Failure) with MockAIProvider PASSED.")

    # --- Test Case 3: A step fails due to AI action 'fail' ---
    print("\\n--- Test Case 3: Step Fails due to AI 'fail' action ---")
    mock_provider_step_fail = MockAIProvider()
    mock_provider_step_fail.plan_steps_to_provide = ["Step A", "Step B (will fail)", "Step C"]
    mock_provider_step_fail.action_sequence = [
        {"action": "type", "selector": "input", "text": "A", "reasoning": "For Step A"},
        {"action": "fail", "reasoning": "AI fails on Step B"}, # AI fails this step
        {"action": "click", "selector": "button", "reasoning": "For Step C (should not be reached)"}
    ]
    orchestrator_step_fail = Orchestrator(provider=mock_provider_step_fail, max_attempts=2)
    success_step_fail, history_step_fail = orchestrator_step_fail.run_test("Objective for step failure", test_start_url)

    print(f"Orchestrator test (step failure by AI) finished. Success: {success_step_fail}")
    assert not success_step_fail, "Test case 3 (step failure by AI) should fail overall"
    assert mock_provider_step_fail.get_plan_call_count == 1
    assert mock_provider_step_fail.get_next_action_call_count == 2 # Called for Step A and Step B
    assert history_step_fail[-1]["action"] == "step_execution_status" and history_step_fail[-1]["step"] == "Step B (will fail)" and history_step_fail[-1]["status"] == "failed"
    print("Orchestrator Test Case 3 (Step Failure by AI) with MockAIProvider PASSED.")

    # --- Test Case 4: A step fails due to max_attempts (e.g. browser action error) ---
    print("\\n--- Test Case 4: Step Fails due to max_attempts ---")
    mock_provider_max_attempts = MockAIProvider()
    mock_provider_max_attempts.plan_steps_to_provide = ["Step X (will cause browser errors)", "Step Y"]
    # This action will cause BrowserController to raise an error (e.g. selector not found on about:blank)
    # The mock AI will keep suggesting it, leading to max_attempts for the step.
    mock_provider_max_attempts.action_sequence = [
        {"action": "click", "selector": "#nonexistent", "reasoning": "Trying to click non-existent (Attempt 1 for Step X)"},
        {"action": "click", "selector": "#nonexistent", "reasoning": "Trying to click non-existent (Attempt 2 for Step X)"},
        {"action": "type", "selector": "input", "text":"Y", "reasoning": "For Step Y (should not be reached)"}
    ]
    orchestrator_max_attempts = Orchestrator(provider=mock_provider_max_attempts, max_attempts=2) # max_attempts per step is 2
    success_max_attempts, history_max_attempts = orchestrator_max_attempts.run_test("Objective for max attempts failure", test_start_url)

    print(f"Orchestrator test (max attempts step failure) finished. Success: {success_max_attempts}")
    assert not success_max_attempts, "Test case 4 (max attempts) should fail overall"
    assert mock_provider_max_attempts.get_plan_call_count == 1
    # get_next_action is called twice for "Step X (will cause browser errors)" because max_attempts is 2
    assert mock_provider_max_attempts.get_next_action_call_count == 2
    last_relevant_entry = history_max_attempts[-1]
    if last_relevant_entry["action"] == "overall_objective_status": # Should not happen if a step fails
        last_relevant_entry = history_max_attempts[-2] # Check the one before overall status

    assert last_relevant_entry["action"] == "step_execution_status"
    assert last_relevant_entry["step"] == "Step X (will cause browser errors)"
    assert last_relevant_entry["status"] == "failed"
    print("Orchestrator Test Case 4 (Max Attempts Step Failure) with MockAIProvider PASSED.")

    print("\\nAll Orchestrator tests with MockAIProvider completed.")
