import os
import subprocess
import sys
import time
import threading
import webbrowser

def run_flask():
    """Run the Flask backend server"""
    print("Starting Flask backend server...")
    if sys.platform == 'win32':
        subprocess.run("python api.py", shell=True)
    else:
        subprocess.run("python3 api.py", shell=True)

def run_react_dev():
    """Run the React development server"""
    print("Starting React development server...")
    os.chdir("frontend")
    if sys.platform == 'win32':
        subprocess.run("npm start", shell=True)
    else:
        subprocess.run("npm start", shell=True)

def open_browser():
    """Open the browser after a delay"""
    time.sleep(5)  # Wait for servers to start
    webbrowser.open("http://localhost:3000")

if __name__ == "__main__":
    # Create required directories if they don't exist
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("data_dictionaries", exist_ok=True)
    
    # Check if frontend/node_modules exists
    if not os.path.exists("frontend/node_modules"):
        print("Installing React dependencies...")
        os.chdir("frontend")
        if sys.platform == 'win32':
            subprocess.run("npm install", shell=True)
        else:
            subprocess.run("npm install", shell=True)
        os.chdir("..")
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Open browser after a delay
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run React in the main thread
    run_react_dev()
