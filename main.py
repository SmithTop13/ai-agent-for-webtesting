import os
import json
import datetime
from agent.orchestrator import Orchestrator
from agent.providers.gemini import GeminiProvider
from dotenv import load_dotenv

def main():
    # Ensure config/.env exists and is loaded for API keys
    # The GeminiProvider and BrowserController might need it.
    # Load from project root's perspective for main.py
    dotenv_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
    if not os.path.exists(dotenv_path):
        print(f"Warning: {dotenv_path} not found. API keys might not be available.")
        print("Please create a config/.env file with your GOOGLE_API_KEY.")
        # Create a dummy one if it doesn't exist so GeminiProvider doesn't fail on import
        # though it will fail on actual use if key is dummy.
        os.makedirs(os.path.join(os.path.dirname(__file__), 'config'), exist_ok=True)
        with open(dotenv_path, 'w') as f:
            f.write('GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"\n')
            f.write('OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"\n')
        print(f"Created a template {dotenv_path}. Please fill in your API keys.")
        return # Exit if no real .env, as it won't work

    load_dotenv(dotenv_path=dotenv_path)

    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "YOUR_GOOGLE_API_KEY_HERE":
        print("Error: GOOGLE_API_KEY is not set or is still the placeholder in config/.env.")
        print("Please update config/.env with your actual Google API Key.")
        return

    # --- Configuration for the test ---
    # Test Objective: Log in to a test website.
    # This example uses https://practicetestautomation.com/practice-test-login/
    # Objective: "Log in to the website using username 'student' and password 'Password123', then verify successful login by finding the 'Log out' button."
    # Start URL: "https://practicetestautomation.com/practice-test-login/"

    # Test Objective: Search on Google
    objective = "คลิก 'login to g-track' และกรอกข้อมูล username 'vowner2@example.com' และ password '5KyB1TYoOY09' ให้ถูกต้อง จากนั้นกดปุ่ม login เพื่อเข้าสู่ระบบ จาก นั้นให้กด ที่ 'คนชับ' แล้วรอ จนตารางโหลดเสร็จ แล้วคลิก 'แก้ไข' เพื่อแก้ไขข้อมูลของคนขับ(อยู่ในตาราง) ชื่อ 'ณรงค์ คนขับซี' เปลี่ยน email จาก 'driver3@example.com' เป็น 'driver3@example.co.th'"
    start_url = "https://www.g-tracking.com/"

    # --- Initialize components ---
    try:
        print("Initializing AI Provider (Gemini)...")
        gemini_brain = GeminiProvider()
    except ValueError as e:
        print(f"Error initializing GeminiProvider: {e}")
        print("Ensure your GOOGLE_API_KEY is correctly set in config/.env")
        return
    except Exception as e:
        print(f"An unexpected error occurred during GeminiProvider initialization: {e}")
        return

    print("Initializing Orchestrator...")
    agent_orchestrator = Orchestrator(provider=gemini_brain, max_attempts=10)

    # --- Run the test ---
    print(f"Starting test with objective: \"{objective}\"")
    print(f"Start URL: {start_url}")

    success, history = agent_orchestrator.run_test(objective, start_url)

    # --- Report results ---
    print("\\n--- Test Run Complete ---")
    if success:
        print("Objective: ACHIEVED")
    else:
        print("Objective: FAILED or max attempts reached")

    print("\\n--- Action History ---")
    for i, record in enumerate(history):
        print(f"{i+1}. Action: {record.get('action')}")
        if record.get('selector'):
            print(f"   Selector: {record.get('selector')}")
        if record.get('text'):
            print(f"   Text: {record.get('text')}")
        if record.get('value'):
            print(f"   Value: {record.get('value')}")
        if record.get('url'):
            print(f"   URL: {record.get('url')}")
        print(f"   Reasoning: {record.get('reasoning', 'N/A')}")
        print(f"   Status: {record.get('status')}")
        if record.get('error_message'):
            print(f"   Error: {record.get('error_message')}")
        print("-" * 20)

    # Save history to a report file
    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(reports_dir, f"test_report_{timestamp}.json")
    try:
        with open(report_file, 'w') as f:
            json.dump({"objective": objective, "start_url": start_url, "success": success, "history": history}, f, indent=2)
        print(f"Test report saved to: {report_file}")
    except Exception as e:
        print(f"Error saving report: {e}")


if __name__ == "__main__":
    # The main script uses java.time which is not standard python.
    # I will replace it with datetime.
    main()
