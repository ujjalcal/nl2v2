import os
import sys
import time
import signal
import subprocess
import threading
import argparse
import webbrowser
import requests
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Debug API key (masked for security)
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    masked_key = api_key[:10] + "..." if len(api_key) > 10 else "None"
    print(f"[APP] API Key loaded (first 10 chars): {masked_key}")
else:
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please create a .env file with your OpenAI API key or set it in your environment.")
    sys.exit(1)

def create_default_goal_templates():
    # Create default goal templates if they don't exist
    goal_templates_dir = 'goal_templates'
    default_goal_templates = [
        {'name': 'default_goal', 'description': 'Default goal template'}
    ]
    for template in default_goal_templates:
        template_file = os.path.join(goal_templates_dir, f"{template['name']}.json")
        if not os.path.exists(template_file):
            with open(template_file, 'w') as f:
                json.dump(template, f, indent=4)

def main():
    """Main entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start the NL2SQL application')
    parser.add_argument('--api-only', action='store_true', help='Start only the API server')
    parser.add_argument('--ui-only', action='store_true', help='Start only the UI server')
    parser.add_argument('--port', type=int, default=5000, help='Port for the API server')
    parser.add_argument('--ui-port', type=int, default=8501, help='Port for the UI server')
    parser.add_argument('--use-master-agent', action='store_true', help='Enable the master agent architecture')
    args = parser.parse_args()

    # Set environment variables
    os.environ['API_PORT'] = str(args.port)
    os.environ['UI_PORT'] = str(args.ui_port)
    os.environ['USE_MASTER_AGENT'] = 'true' if args.use_master_agent else 'false'

    # Print configuration
    print(f"Configuration:")
    print(f"  API Port: {args.port}")
    print(f"  UI Port: {args.ui_port}")
    print(f"  Master Agent: {'Enabled' if args.use_master_agent else 'Disabled'}")

    # Create directories
    os.makedirs('temp', exist_ok=True)
    os.makedirs('test', exist_ok=True)

    # Create goal templates directory if using master agent
    if args.use_master_agent:
        os.makedirs('goal_templates', exist_ok=True)

        # Create default goal templates if they don't exist
        create_default_goal_templates()

    # Global variables for process management
    api_process = None
    ui_process = None

    def start_api_server():
        """Start the API server in a separate process."""
        global api_process
        print("Starting API server on http://localhost:5000...")

        # Start the API server process
        api_process = subprocess.Popen(
            [sys.executable, "nl2sql_api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Print API server output in a non-blocking way
        def read_output():
            for line in api_process.stdout:
                print(f"[API] {line.strip()}")

        threading.Thread(target=read_output, daemon=True).start()

        # Wait for API server to be ready
        print("Waiting for API server to be ready...")
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:5000/")
                if response.status_code == 200:
                    print("API server is ready!")
                    return True
                time.sleep(0.5)
            except requests.exceptions.ConnectionError:
                time.sleep(0.5)

        print("Error: API server failed to start properly.")
        return False

    def start_minimalist_ui():
        """Start the minimalist UI server in a separate process."""
        global ui_process
        print("Starting minimalist UI server on http://localhost:8501...")

        # Start the minimalist UI server process
        ui_process = subprocess.Popen(
            [sys.executable, "minimalist_ui.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Print UI server output in a non-blocking way
        def read_output():
            for line in ui_process.stdout:
                print(f"[UI] {line.strip()}")

        threading.Thread(target=read_output, daemon=True).start()

        # Wait for UI server to be ready
        print("Waiting for UI server to be ready...")
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8501")
                if response.status_code == 200:
                    print("Minimalist UI server is ready!")
                    return True
                time.sleep(0.5)
            except requests.exceptions.ConnectionError:
                time.sleep(0.5)

        print("Warning: UI server might not be fully ready yet, but continuing...")
        return True

    # Start the application
    print("Starting NL2SQL Tool with Agentic Architecture...")

    # Start the API server
    if not args.ui_only:
        if not start_api_server():
            print("Failed to start API server. Exiting...")
            sys.exit(1)

    # Start the minimalist UI server
    if not args.api_only:
        if not start_minimalist_ui():
            print("Failed to start minimalist UI server. Exiting...")
            sys.exit(1)

    print("NL2SQL Tool is running!")
    print(f"API server: http://localhost:{args.port}")
    print(f"Minimalist UI server: http://localhost:{args.ui_port}")

    # Open the browser
    print("Opening browser...")
    try:
        webbrowser.open(f"http://localhost:{args.ui_port}")
    except Exception as e:
        print(f"Error opening browser: {str(e)}")

    print("Press Ctrl+C to stop the servers.")

    try:
        # Keep the main process running
        while True:
            # Check if processes are still running
            if api_process and api_process.poll() is not None:
                print("API server stopped unexpectedly. Exiting...")
                break
            if ui_process and ui_process.poll() is not None:
                print("Minimalist UI server stopped unexpectedly. Exiting...")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down NL2SQL Tool...")
    finally:
        # Clean up processes
        if api_process and api_process.poll() is None:
            api_process.terminate()
        if ui_process and ui_process.poll() is None:
            ui_process.terminate()
        print("Servers shut down.")
        sys.exit(0)

if __name__ == "__main__":
    main()
