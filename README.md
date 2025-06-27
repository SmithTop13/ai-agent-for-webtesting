# AI-Powered UI Testing Agent

This project implements an AI-powered agent capable of navigating and interacting with web UIs to achieve specified objectives. It uses **Selenium** for browser automation and a pluggable AI provider (currently Google Gemini) to decide on the next actions.

## Project Structure

- **`agent/`**: Contains the core logic of the agent.
  - **`browser/`**: Houses the `BrowserController` (`controller.py`) responsible for all **Selenium** browser interactions.
  - **`providers/`**: Contains the AI provider interface (`base.py`) and implementations (e.g., `gemini.py`).
  - **`orchestrator.py`**: The central `Orchestrator` class that manages the observe-plan-act loop, connecting the browser controller and AI provider.
- **`config/`**: For configuration files.
  - **`.env`**: Stores API keys (e.g., `GOOGLE_API_KEY`). This file should **not** be committed to Git.
- **`reports/`**: Test results and action history logs are saved here in JSON format.
- **`main.py`**: The main entry point to run the agent.
- **`requirements.txt`**: Lists Python dependencies.
- **`.gitignore`**: Specifies intentionally untracked files that Git should ignore.

## Getting Started

Follow these steps to set up and run the AI UI Testing Agent:

### 1. Prerequisites

- Python 3.8 or higher.
- Access to a Google Gemini API key.
- Google Chrome browser installed.
- ChromeDriver executable matching your Chrome version.

### 2. Clone the Repository

```bash
git clone <repository_url>
cd <repository_directory>
```

### 3. Set Up a Virtual Environment (Recommended)

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
python -m venv venv
```

Activate the virtual environment:

- **On macOS and Linux:**
  ```bash
  source venv/bin/activate
  ```
- **On Windows:**
  ```bash
  .\\venv\\Scripts\\activate
  ```

### 4. Install Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 5. Set Up Selenium WebDriver

Selenium requires a WebDriver to interface with the chosen browser. The `BrowserController` is currently configured to use Chrome.

1.  **Ensure Google Chrome is Installed:** If you don't have Google Chrome installed, download and install it from [google.com/chrome](https://www.google.com/chrome/).

2.  **Download ChromeDriver:**
    *   Check your Google Chrome browser version (Go to `Help > About Google Chrome`).
    *   Download the corresponding ChromeDriver executable from the official site: [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads) or [https://googlechromelabs.github.io/chrome-for-testing/](https://googlechromelabs.github.io/chrome-for-testing/) (for newer versions). Make sure the ChromeDriver version matches your Chrome browser version closely.

3.  **Add ChromeDriver to System PATH:**
    *   **macOS/Linux:** Move the `chromedriver` executable to a directory that is part of your system's PATH (e.g., `/usr/local/bin`).
      ```bash
      sudo mv /path/to/downloaded/chromedriver /usr/local/bin/
      sudo chmod +x /usr/local/bin/chromedriver
      ```
      *(Note: You might need `sudo` depending on your permissions and target directory.)*
    *   **Windows:**
        1.  Create a folder for WebDrivers if you don't have one (e.g., `C:\WebDrivers`).
        2.  Move the `chromedriver.exe` executable into this folder.
        3.  Add this folder to your system's PATH environment variable.
            (Search for "environment variables" in Windows search, click "Edit the system environment variables", click "Environment Variables...", find "Path" under "System variables", click "Edit...", click "New", and add the path to your WebDriver folder, e.g., `C:\WebDrivers`).

    Alternatively, you can place `chromedriver` (or `chromedriver.exe`) directly in your project's root directory or a known script location, but adding it to the PATH is generally more robust for development. The current `BrowserController` expects `chromedriver` to be found in the system PATH.

*(Note: If you wish to use a different browser like Firefox, you would need to install Mozilla Firefox, download GeckoDriver from [Mozilla's geckodriver releases page](https://github.com/mozilla/geckodriver/releases), add it to your PATH, and modify `agent/browser/controller.py` to initialize `webdriver.Firefox()` instead of `webdriver.Chrome()`.)*

### 6. Configure API Keys

The agent requires API keys to interact with AI services (e.g., Google Gemini).

1.  Create a `.env` file in the `config/` directory:
    ```bash
    touch config/.env
    ```
    If the `config` directory doesn't exist, create it first: `mkdir config`.

2.  Add your API keys to this file. For Google Gemini, you'll need:
    ```env
    GOOGLE_API_KEY="your_actual_google_api_key_here"
    # OPENAI_API_KEY="your_openai_api_key_if_using_openai_provider" # Example for other providers
    ```
    Replace `"your_actual_google_api_key_here"` with your valid Google API Key.

    **Important:** The `.gitignore` file is configured to ignore `config/.env` files (and `.env` in general), so your API keys will not be committed to the repository.

## Running the Agent

The main script to execute the agent is `main.py`.

### 1. Define Objective and Start URL

Open `main.py` in your editor. You will find the following variables near the top of the `main()` function:

```python
    # --- Configuration for the test ---
    # Example Objective:
    objective = "Search for 'Playwright Python documentation' on Google, and then click on the official Playwright Python link in the search results. Finally, verify you are on a page with 'Playwright' in its title."
    start_url = "https://www.google.com"
```

-   Modify the `objective` string to describe the task you want the agent to perform.
-   Modify the `start_url` to the initial webpage where the agent should begin its task.

### 2. Execute the Agent

Run the agent from the project root directory:

```bash
python main.py
```

The agent will launch a browser (Google Chrome by default, using Selenium; non-headless by default so you can see its actions) and attempt to achieve the specified objective.

### 3. View Reports

After the agent finishes (either by achieving the objective, failing, or reaching the maximum number of attempts), a JSON report detailing the actions taken will be saved in the `reports/` directory. The filename will include a timestamp.

## How it Works

The agent operates on an "observe-plan-act" loop:

1.  **Observe**: The `BrowserController`, using Selenium, captures a simplified version of the current page's Document Object Model (DOM), focusing on interactive elements (links, buttons, inputs, etc.).
2.  **Plan**: The `Orchestrator` sends the current objective, the history of past actions, and the simplified DOM to the configured `AIProvider` (e.g., `GeminiProvider`). The AI provider then returns the next action it believes will help achieve the objective.
3.  **Act**: The `Orchestrator` instructs the `BrowserController` to execute the action suggested by the AI (e.g., click an element, type text).

This loop continues until the AI determines the objective is met ("finish" action), it cannot proceed ("fail" action), or a maximum number of attempts is reached.
