import os
import sys
import subprocess
import threading
import time
import webbrowser
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if OpenAI API key is set
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please create a .env file with your OpenAI API key or set it in your environment.")
    sys.exit(1)

# Create necessary directories
os.makedirs('temp', exist_ok=True)
os.makedirs('test', exist_ok=True)

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
    print("Starting minimalist UI server on http://localhost:5001...")
    
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
            response = requests.get("http://localhost:5001")
            if response.status_code == 200:
                print("Minimalist UI server is ready!")
                return True
            time.sleep(0.5)
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    
    print("Warning: UI server might not be fully ready yet, but continuing...")
    return True

if __name__ == "__main__":
    print("Starting NL2SQL Tool with Agentic Architecture...")
    
    # Start the API server
    if not start_api_server():
        print("Failed to start API server. Exiting...")
        sys.exit(1)
    
    # Start the minimalist UI server
    if not start_minimalist_ui():
        print("Failed to start minimalist UI server. Exiting...")
        sys.exit(1)
    
    print("NL2SQL Tool is running!")
    print("API server: http://localhost:5000")
    print("Minimalist UI server: http://localhost:5001")
    
    # Open the browser
    print("Opening browser...")
    try:
        webbrowser.open("http://localhost:5001")
    except Exception as e:
        print(f"Error opening browser: {str(e)}")
    
    print("Press Ctrl+C to stop the servers.")
    
    try:
        # Keep the main process running
        while True:
            # Check if processes are still running
            if api_process.poll() is not None:
                print("API server stopped unexpectedly. Exiting...")
                break
            if ui_process.poll() is not None:
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
