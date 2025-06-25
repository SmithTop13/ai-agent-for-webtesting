from abc import ABC, abstractmethod

class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    Defines the interface for getting the next action from an AI model.
    """
    @abstractmethod
    def get_next_action(self, objective: str, history: list[dict], dom: list[dict]) -> dict:
        """
        Determines the next browser action to take based on the objective,
        history of previous actions, and the current state of the DOM.

        Args:
            objective: The overall goal for the AI agent.
            history: A list of dictionaries, where each dictionary represents a past action
                     and its outcome. E.g., {"action": "click", "selector": "#id", "status": "success"}
            dom: A list of dictionaries representing the simplified interactive elements
                 of the current webpage. Each dictionary contains details like tag, attributes,
                 and selector for an element.

        Returns:
            A dictionary representing the next action to take.
            Expected format:
            {
                "action": "click",                       # e.g., click, type, select, finish, fail
                "selector": "css_selector_for_element",  # required for click, type, select
                "text": "text_to_type",                  # required for type
                "value": "value_to_select",              # required for select
                "reasoning": "AI's reasoning for this action" # Optional: explanation from AI
            }
            If the objective is achieved, action should be "finish".
            If the objective cannot be achieved or an error occurs, action should be "fail".
        """
        pass
