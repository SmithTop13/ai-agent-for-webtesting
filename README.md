# AI-Powered UI Testing Agent

This project implements an AI-powered agent capable of navigating and interacting with web UIs to achieve specified objectives. It uses Playwright for browser automation and a pluggable AI provider (currently Google Gemini) to decide on the next actions.

## Project Structure

- **`agent/`**: Contains the core logic of the agent.
  - **`browser/`**: Houses the `BrowserController` (`controller.py`) responsible for all Playwright browser interactions.
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

### 5. Install Playwright Browsers and Dependencies

Playwright requires browser binaries to be installed. The `--with-deps` flag will also install necessary operating system dependencies.

```bash
playwright install --with-deps
```
This will download Chromium, Firefox, and WebKit browsers.

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

The agent will launch a browser (Chromium by default, non-headless so you can see its actions) and attempt to achieve the specified objective.

### 3. View Reports

After the agent finishes (either by achieving the objective, failing, or reaching the maximum number of attempts), a JSON report detailing the actions taken will be saved in the `reports/` directory. The filename will include a timestamp.

## How it Works

The agent operates on an "observe-plan-act" loop:

1.  **Observe**: The `BrowserController` captures a simplified version of the current page's Document Object Model (DOM), focusing on interactive elements (links, buttons, inputs, etc.).
2.  **Plan**: The `Orchestrator` sends the current objective, the history of past actions, and the simplified DOM to the configured `AIProvider` (e.g., `GeminiProvider`). The AI provider then returns the next action it believes will help achieve the objective.
3.  **Act**: The `Orchestrator` instructs the `BrowserController` to execute the action suggested by the AI (e.g., click an element, type text).

This loop continues until the AI determines the objective is met ("finish" action), it cannot proceed ("fail" action), or a maximum number of attempts is reached.
