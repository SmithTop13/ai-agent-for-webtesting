import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
# Import other browser options if you plan to support them (e.g., FirefoxOptions)

class BrowserController:
    def __init__(self, headless=False): # Added headless option
        # TODO: Make browser choice configurable (e.g., Chrome, Firefox)
        chrome_options = ChromeOptions()
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080") # Recommended for headless

        # For simplicity, assuming chromedriver is in PATH.
        # For more robust setup, use webdriver_manager or specify executable_path.
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(5) # Implicit wait for elements to appear

    def navigate(self, url: str):
        """Navigates to the given URL."""
        try:
            self.driver.get(url)
            print(f"Navigated to {url}")
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            # Potentially raise a custom exception or handle more gracefully

    def shutdown(self):
        """Closes the browser."""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
        print("Browser shutdown complete.")

    def _find_element(self, selector: str, timeout: int = 10):
        """Finds an element using CSS selector with an explicit wait."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except Exception as e:
            print(f"Error finding element with selector '{selector}': {e}")
            return None

    def _find_elements(self, selector: str, timeout: int = 10):
        """Finds multiple elements using CSS selector with an explicit wait."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as e:
            print(f"Error finding elements with selector '{selector}': {e}")
            return []


    def click_element(self, selector: str):
        """Clicks the element specified by the selector."""
        try:
            element = self._find_element(selector)
            if element:
                WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                element.click()
                print(f"Clicked element with selector: {selector}")
            else:
                print(f"Element with selector '{selector}' not found for clicking.")
        except Exception as e:
            print(f"Error clicking element {selector}: {e}")

    def type_in_element(self, selector: str, text: str):
        """Types the given text into the element specified by the selector."""
        try:
            element = self._find_element(selector)
            if element:
                element.clear() # Clear the field before typing
                element.send_keys(text)
                print(f"Typed '{text}' into element with selector: {selector}")
            else:
                print(f"Element with selector '{selector}' not found for typing.")
        except Exception as e:
            print(f"Error typing into element {selector}: {e}")

    def select_option(self, selector: str, value: str):
        """Selects an option by its value in a select element."""
        try:
            element = self._find_element(selector)
            if element:
                Select(element).select_by_value(value)
                print(f"Selected option '{value}' in element with selector: {selector}")
            else:
                print(f"Element with selector '{selector}' not found for selecting option.")
        except Exception as e:
            print(f"Error selecting option in element {selector}: {e}")

    def get_simplified_dom(self) -> list[dict]:
        """
        Extracts all interactive elements (a, button, input, select, textarea)
        from the current page and returns a simplified list of dictionaries.
        """
        interactive_elements_data = []
        # Selenium's By.CSS_SELECTOR is generally good.
        # For complex selectors, one might need By.XPATH.
        # The list of tags remains the same.
        css_selector_for_interactive_elements = "a, button, input, select, textarea, [role='button'], [role='link'], [role='menuitem'], [role='tab'], [role='checkbox'], [role='radio'], [role='option'], [role='combobox'], [role='textbox'], [role='searchbox']"

        try:
            elements = self._find_elements(css_selector_for_interactive_elements)
            for element in elements:
                try:
                    is_visible = element.is_displayed()
                    is_enabled = element.is_enabled()

                    # Only process visible and enabled elements to reduce noise for the LLM
                    if not (is_visible and is_enabled):
                        continue

                    element_data = {
                        "tag": element.tag_name.lower(),
                        "attributes": {},
                        "text_content": (element.text or "").strip()[:200], # Limit text length
                        "is_visible": is_visible,
                        "is_enabled": is_enabled,
                    }

                    # Extract common identifying attributes
                    for attr in ["id", "name", "aria-label", "data-testid", "placeholder", "title", "alt", "value", "href", "type", "role"]:
                        attr_value = element.get_attribute(attr)
                        if attr_value:
                            element_data["attributes"][attr] = attr_value

                    # For input elements, get the type (already covered by general attributes if 'type' exists)
                    # No special handling needed here if "type" is in the list above.

                    # For select elements, get options
                    if element_data["tag"] == "select":
                        select_element = Select(element)
                        element_data["options"] = []
                        for option_element in select_element.options:
                            opt_value = option_element.get_attribute("value")
                            opt_text = (option_element.text or "").strip()
                            element_data["options"].append({"value": opt_value, "text": opt_text})

                    # Generate a unique selector (CSS selector)
                    # This is a simplified approach. More robust selector generation can be complex.
                    # Prioritize ID, then name, then data-testid.
                    _id = element.get_attribute("id")
                    if _id:
                        element_data["selector"] = f"#{_id}"
                    else:
                        name = element.get_attribute("name")
                        if name:
                            # CSS attribute selector: tag[name='value']
                            element_data["selector"] = f"{element_data['tag']}[name='{name}']"
                        else:
                            data_testid = element.get_attribute("data-testid")
                            if data_testid:
                                element_data["selector"] = f"[data-testid='{data_testid}']"
                            else:
                                # Fallback: could construct a more complex XPath or rely on attributes
                                # For now, we'll let the AI decide based on the attributes provided
                                pass

                    interactive_elements_data.append(element_data)
                except Exception as e_inner:
                    # print(f"Skipping an element due to error during its processing: {e_inner}")
                    continue # Skip this element and proceed with others

            return interactive_elements_data

        except Exception as e:
            print(f"Error getting simplified DOM: {e}")
            return [] # Return empty list on error

    # Helper for explicit waits, not directly used by orchestrator but good for testing
    def wait_for_element(self, selector: str, timeout: int = 10):
        """Waits for an element to be present and visible."""
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
        )

    def wait_for_timeout(self, milliseconds: int): # Added for compatibility with example
        """ Sleeps for a specified number of milliseconds. """
        time.sleep(milliseconds / 1000.0)


if __name__ == '__main__':
    # Example Usage (for testing purposes)
    controller = BrowserController(headless=True) # Can run headless for tests
    controller.navigate("https://www.google.com")

    # Test typing in search bar
    simplified_dom_before_search = controller.get_simplified_dom()
    print("\\nSimplified DOM (Google):")
    search_bar_selector = None
    for el in simplified_dom_before_search:
        if el['attributes'].get('name') == 'q' or 'search' in (el['attributes'].get('aria-label') or '').lower():
            print(el)
            if el.get('selector'):
                search_bar_selector = el['selector']
                break # Found a good candidate

    if not search_bar_selector: # Fallback if not found via DOM inspection logic
        search_bar_selector = "textarea[name='q']" # A common selector for Google's search bar

    print(f"Attempting to use selector for search bar: {search_bar_selector}")
    controller.type_in_element(search_bar_selector, "Selenium browser automation with Python")

    # Test clicking the search button
    # Google's search button can be tricky. Let's try to find it via DOM.
    controller.wait_for_timeout(1000) # wait 1 second for page to update if necessary

    simplified_dom_after_typing = controller.get_simplified_dom()
    search_button_selector = None
    # print("\\nSimplified DOM (after typing, looking for search button):")
    for el in simplified_dom_after_typing:
        # if el['tag'] == 'input' and el['attributes'].get('type') == 'submit' and ('search' in (el['attributes'].get('aria-label') or '').lower() or 'btnk' in (el['attributes'].get('name') or '').lower()):
        # More robust: look for a button (input type submit or button tag) that is visible and associated with search
        if (el['tag'] == 'input' and el['attributes'].get('type') == 'submit') or el['tag'] == 'button':
            if 'search' in (el.get('text_content','').lower() + el['attributes'].get('aria-label','').lower() + el['attributes'].get('value','').lower()):
                # print(el)
                if el.get('selector') and el.get('is_visible'):
                    search_button_selector = el['selector']
                    # Prefer a selector that is more specific if possible
                    if "input[name='btnK']" in search_button_selector or "[aria-label='Google Search']" in search_button_selector : # common ones
                         break

    if not search_button_selector:
        # Fallback selectors if dynamic lookup fails, these are common for Google
        # Try the one that's usually more reliable first
        search_button_selector_candidates = [
            "input[aria-label='Google Search']",
            "input[name='btnK']",
            "button[aria-label='Google Search']"
        ]
        # We need to find which one is visible and clickable
        for cand_selector in search_button_selector_candidates:
            try:
                element = controller._find_element(cand_selector, timeout=2) # Short timeout
                if element and element.is_displayed() and element.is_enabled():
                    search_button_selector = cand_selector
                    break
            except:
                continue


    if search_button_selector:
        print(f"Attempting to click search button with selector: {search_button_selector}")
        controller.click_element(search_button_selector)
    else:
        print("Could not find a suitable search button to click via DOM inspection or fallbacks.")


    controller.wait_for_timeout(3000) # Wait for search results to load

    print("\\nSimplified DOM (Search Results for Selenium):")
    simplified_dom_results = controller.get_simplified_dom()
    for i, el in enumerate(simplified_dom_results):
        if i < 15: # Print first 15 interactive elements
            print(el)

    controller.shutdown()
