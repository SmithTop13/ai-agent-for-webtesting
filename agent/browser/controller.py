from playwright.sync_api import Playwright, sync_playwright, BrowserContext, Page

class BrowserController:
    def __init__(self):
        self.playwright: Playwright = sync_playwright().start()
        self.browser: BrowserContext = self.playwright.chromium.launch(headless=False).new_context() # TODO: make headless configurable
        self.page: Page = self.browser.new_page()

    def navigate(self, url: str):
        """Navigates to the given URL."""
        try:
            self.page.goto(url, wait_until="domcontentloaded") # Consider 'load' or 'networkidle' based on needs
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            # Potentially raise a custom exception or handle more gracefully

    def shutdown(self):
        """Closes the browser and cleans up Playwright resources."""
        if hasattr(self, 'page') and self.page:
            self.page.close()
        if hasattr(self, 'browser') and self.browser:
            self.browser.close()
        if hasattr(self, 'playwright') and self.playwright:
            self.playwright.stop()
        print("Browser shutdown complete.")

    def click_element(self, selector: str):
        """Clicks the element specified by the selector."""
        try:
            self.page.locator(selector).click()
            print(f"Clicked element with selector: {selector}")
        except Exception as e:
            print(f"Error clicking element {selector}: {e}")
            # Handle error (e.g., element not found, not clickable)

    def type_in_element(self, selector: str, text: str):
        """Types the given text into the element specified by the selector."""
        try:
            self.page.locator(selector).fill(text)
            print(f"Typed '{text}' into element with selector: {selector}")
        except Exception as e:
            print(f"Error typing into element {selector}: {e}")
            # Handle error

    def select_option(self, selector: str, value: str):
        """Selects an option by its value in a select element."""
        try:
            self.page.locator(selector).select_option(value)
            print(f"Selected option '{value}' in element with selector: {selector}")
        except Exception as e:
            print(f"Error selecting option in element {selector}: {e}")
            # Handle error (e.g., option not found)

    def get_simplified_dom(self) -> list[dict]:
        """
        Extracts all interactive elements (a, button, input, select, textarea)
        from the current page and returns a simplified list of dictionaries.
        """
        interactive_elements_data = []
        selectors = "a, button, input, select, textarea, [role='button'], [role='link'], [role='menuitem'], [role='tab'], [role='checkbox'], [role='radio'], [role='option'], [role='combobox'], [role='textbox'], [role='searchbox']"

        try:
            elements = self.page.query_selector_all(selectors)
            for element in elements:
                # Basic properties
                element_data = {
                    "tag": element.evaluate("el => el.tagName.toLowerCase()"),
                    "attributes": {},
                    "text_content": (element.text_content() or "").strip()[:200], # Limit text length
                    "is_visible": element.is_visible(),
                    "is_enabled": element.is_enabled(),
                }

                # Extract common identifying attributes
                for attr in ["id", "name", "aria-label", "data-testid", "placeholder", "title", "alt", "value", "href", "type", "role"]:
                    attr_value = element.get_attribute(attr)
                    if attr_value:
                        element_data["attributes"][attr] = attr_value

                # For input elements, get the type
                if element_data["tag"] == "input":
                    input_type = element.get_attribute("type")
                    if input_type:
                         element_data["attributes"]["type"] = input_type

                # For select elements, get options
                if element_data["tag"] == "select":
                    options = element.query_selector_all("option")
                    element_data["options"] = []
                    for opt in options:
                        opt_value = opt.get_attribute("value")
                        opt_text = (opt.text_content() or "").strip()
                        element_data["options"].append({"value": opt_value, "text": opt_text})

                # Generate a unique selector if possible (preferring id, then name, then data-testid)
                # This is a simplistic approach and might need refinement for complex pages
                unique_id = element.get_attribute("id")
                if unique_id:
                    element_data["selector"] = f"#{unique_id}"
                else:
                    name = element.get_attribute("name")
                    if name:
                        element_data["selector"] = f"[{element_data['tag']}[name='{name}']" # More specific
                    else:
                        data_testid = element.get_attribute("data-testid")
                        if data_testid:
                            element_data["selector"] = f"[data-testid='{data_testid}']"
                        else:
                            # Fallback to a less ideal selector, could be brittle
                            # For now, we'll let the AI decide based on the attributes
                            pass


                # Only add if it's visible and enabled, to reduce noise for the LLM
                if element_data["is_visible"] and element_data["is_enabled"]:
                    interactive_elements_data.append(element_data)

            return interactive_elements_data

        except Exception as e:
            print(f"Error getting simplified DOM: {e}")
            return [] # Return empty list on error

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    controller = BrowserController()
    controller.navigate("https://www.google.com")

    # Test typing in search bar
    # First, let's inspect the DOM to find a selector for the search bar
    simplified_dom_before_search = controller.get_simplified_dom()
    print("\\nSimplified DOM (Google):")
    for el in simplified_dom_before_search:
        if el['attributes'].get('name') == 'q' or 'search' in (el['attributes'].get('aria-label') or '').lower():
            print(el) # Print potential search bar elements
            # Found it: {'tag': 'textarea', 'attributes': {'aria-label': 'Search', 'name': 'q', ...}, ...}
            # So, selector could be "textarea[name='q']" or "[aria-label='Search']"

    # controller.type_in_element("textarea[name='q']", "Playwright browser automation") # Using name
    # Or using aria-label which might be more stable for some sites
    controller.type_in_element("[aria-label='Search']", "Playwright browser automation")


    # Test clicking the search button
    # Inspect DOM again or use prior knowledge. Google's search button often has input type submit and a name like 'btnK' or an aria-label
    # simplified_dom_after_typing = controller.get_simplified_dom()
    # print("\\nSimplified DOM (after typing):")
    # for el in simplified_dom_after_typing:
    #    if el['tag'] == 'input' and el['attributes'].get('type') == 'submit' and 'search' in (el['attributes'].get('aria-label') or '').lower() :
    #        print(el)
            # Found: {'tag': 'input', 'attributes': {'aria-label': 'Google Search', 'name': 'btnK', 'type': 'submit', ... }
            # Selector: "input[name='btnK']" or "[aria-label='Google Search']"

    # Give some time for the button to potentially appear or become active after typing
    controller.page.wait_for_timeout(1000) # wait 1 second

    # Click the search button (try a common selector for Google search button)
    # This might require careful selector choice, Google's page can be complex.
    # Using a selector that is generally visible and associated with search.
    # controller.click_element("input[name='btnK']") # This selector targets one of the search buttons
    # Trying a more general approach if the specific name isn't always there or if there are multiple.
    # Let's try clicking the one that has "Google Search" as aria-label
    controller.click_element("input[aria-label='Google Search']")


    controller.page.wait_for_timeout(3000) # Wait for search results to load

    print("\\nSimplified DOM (Search Results for Playwright):")
    simplified_dom_results = controller.get_simplified_dom()
    for i, el in enumerate(simplified_dom_results):
        if i < 15: # Print first 15 interactive elements
            print(el)

    controller.shutdown()
