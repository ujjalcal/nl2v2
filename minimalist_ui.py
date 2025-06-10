from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import requests

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# API proxy routes
@app.route('/api/list_databases', methods=['GET'])
def list_databases():
    """Proxy endpoint to forward database listing requests to the API server."""
    try:
        # Forward the request to the API server
        response = requests.get('http://localhost:5000/api/list_databases')
        
        # Log the response for debugging
        print(f"API response: {response.status_code}")
        print(f"API response content: {response.text[:200]}...")
        
        # Return the response from the API server
        return response.json(), response.status_code
    except Exception as e:
        print(f"Error in list_databases proxy: {str(e)}")
        return jsonify({'error': str(e), 'databases': []}), 500

@app.route('/')
def index():
    """
    Render the minimalist chat interface.
    This is a single-page application that communicates with the API.
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NL2SQL Tool</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        <style>
        :root {
            --primary-color: #10a37f;
            --border-color: #e5e7eb;
            --background-color: #ffffff;
            --text-color: #374151;
            --secondary-text-color: #6b7280;
            --hover-color: #f9fafb;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.5;
            color: var(--text-color);
            background-color: var(--background-color);
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        
        .header {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: relative;
        }
        
        .clear-cache-button {
            background-color: transparent;
            color: #9ca3af;
            border: none;
            cursor: pointer;
            padding: 0.5rem;
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            transition: color 0.2s;
            margin-right: 1rem;
        }
        
        .clear-cache-button:hover {
            color: #ef4444;
        }
        
        .header h1 {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-color);
            margin: 0 auto;
        }
        
        /* Database selector styling */
        .database-selector {
            display: flex;
            align-items: center;
            margin-left: auto;
            margin-right: 1rem;
        }
        
        .database-selector select {
            padding: 0.375rem 0.75rem;
            border-radius: 0.375rem;
            border: 1px solid var(--border-color);
            background-color: var(--background-color);
            color: var(--text-color);
            font-size: 0.875rem;
            cursor: pointer;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        
        .database-selector select:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(16, 163, 127, 0.2);
        }
        
        .database-selector label {
            margin-right: 0.5rem;
            font-size: 0.875rem;
            color: var(--secondary-text-color);
        }
        
        .chat-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            width: 100%;
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .message {
            display: flex;
            gap: 0.75rem;
        }
        
        .avatar {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        
        .bot-avatar {
            background-color: var(--primary-color);
            color: white;
        }
        
        .user-avatar {
            background-color: #3b82f6;
            color: white;
        }
        
        .content {
            background-color: var(--background-color);
            padding: 0.5rem 0;
            border-radius: 0.375rem;
            max-width: calc(100% - 40px);
        }
        
        .content p {
            margin-bottom: 0.5rem;
        }
        
        .content p:last-child {
            margin-bottom: 0;
        }
        
        /* Agent activity styling */
        .agent-activity {
            font-size: 0.8rem;
            color: #6b7280;
            margin-bottom: 0.2rem;
            padding: 0.2rem 0;
            line-height: 1.2;
        }
        
        .agent-activity strong {
            color: #374151;
        }
        
        .workflow-state {
            font-size: 0.75rem;
            color: #6b7280;
            font-weight: normal;
        }
        
        /* Make progress messages more compact */
        .progress-message {
            margin-bottom: 0;
            padding-bottom: 0;
        }
        
        .progress-message .content {
            padding-top: 0.25rem;
            padding-bottom: 0.25rem;
        }
        
        /* Group agent activities visually */
        .agent-activities-container {
            background-color: #f9fafb;
            border-radius: 0.5rem;
            padding: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        .input-container {
            position: relative;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            background-color: var(--background-color);
            display: flex;
            align-items: center;
        }
        
        .input-container:focus-within {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(16, 163, 127, 0.2);
        }
        
        #query {
            flex: 1;
            border: none;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            background-color: transparent;
            color: var(--text-color);
            outline: none;
            resize: none;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .attachment-button {
            background-color: transparent;
            border: none;
            color: var(--secondary-text-color);
            padding: 0.5rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            transition: color 0.2s;
        }
        
        .attachment-button:hover {
            color: var(--primary-color);
        }
        
        #sendButton {
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.375rem;
            padding: 0.5rem 1rem;
            margin-right: 0.5rem;
            cursor: pointer;
            font-weight: 500;
            transition: background-color 0.2s;
        }
        
        #sendButton:hover {
            background-color: #0d8c6d;
        }
        
        #sendButton:disabled {
            background-color: #e5e7eb;
            color: #9ca3af;
            cursor: not-allowed;
        }
        
        #file {
        }
        
        .remove-file:hover {
            color: #ef4444;
        }
        
        .typing-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            margin-left: 0.25rem;
        }
        
        .typing-dot {
            width: 5px;
            height: 5px;
            background-color: var(--primary-color);
            border-radius: 50%;
            opacity: 0.7;
            animation: typing-dot 1.2s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(1) { animation-delay: 0s; }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing-dot {
            0%, 60%, 100% { opacity: 0.7; }
            30% { opacity: 1; }
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.875rem;
        }
        
        table th, table td {
            padding: 0.5rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        table th {
            background-color: #f9fafb;
            font-weight: 600;
        }
        
        table tr:hover {
            background-color: #f3f4f6;
        }
        
        code {
            font-family: 'Courier New', Courier, monospace;
            background-color: #f3f4f6;
            padding: 0.125rem 0.25rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
        }
        
        pre {
            background-color: #f3f4f6;
            padding: 0.75rem;
            border-radius: 0.375rem;
            overflow-x: auto;
            margin: 0.5rem 0;
        }
        
        .sql-code {
            color: #0d8c6d;
            font-weight: 500;
        }
        
        .processing-step {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.25rem;
        }
        
        .step-icon {
            color: var(--primary-color);
        }
        
        .completion-message {
            margin-top: 0.5rem;
            padding: 0.5rem;
            background-color: rgba(16, 163, 127, 0.1);
            border-left: 3px solid var(--primary-color);
            border-radius: 0.25rem;
        }
        
        .progress-container {
            display: none; /* Hide the old progress container */
        }
        
        /* Style for progress messages */
        .progress-message {
            opacity: 0.9;
        }
        
        .progress-message .content {
            background-color: #f0f9ff;
            border-left: 3px solid var(--primary-color);
            padding-left: 0.75rem;
        }
        
        .progress-message .content p {
            margin: 0.25rem 0;
        }
        
        .progress-message .content strong {
            color: var(--primary-color);
            font-family: monospace;
            font-size: 0.9rem;
        }
        
        .progress-message .workflow-state {
            background-color: #4b5563;
            color: white;
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            font-size: 0.7rem;
            font-family: monospace;
            margin-left: 0.3rem;
        }
        
        /* Spinning cog animation */
        .fa-spin {
            animation: fa-spin 2s infinite linear;
        }
        
        @keyframes fa-spin {
            0% {
                transform: rotate(0deg);
            }
            100% {
                transform: rotate(360deg);
            }
        }
        
        @media (max-width: 768px) {
            .chat-container {
                padding: 0.5rem;
            }
            
            .header h1 {
                font-size: 1.125rem;
            }
        }
        </style>
    </head>
    <body>
        <div class="header">
            <button id="clearCacheButton" class="clear-cache-button" title="Clear all uploaded and generated files">
                <i class="fas fa-trash"></i>
            </button>
            <h1>NL2SQL Tool</h1>
            <div class="database-selector">
                <label for="databaseSelect">Database:</label>
                <select id="databaseSelect" disabled>
                    <option value="">No databases available</option>
                </select>
            </div>
        </div>
        
        <div class="chat-container">
            <div class="messages" id="messages">
                <!-- Welcome message -->
                <div class="message">
                    <div class="avatar bot-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="content">
                        
                        <p>Unlock Data Insights with Natural Language</p>
                        <p style="margin-top: 0.5rem;">To get started, upload a data file (CSV, JSON, XML, YAML, Excel) using the attachment button below.</p>
                    </div>
                </div>
            </div>
            
            <div class="file-preview" id="filePreview"></div>
            
            <!-- Progress container for file processing -->
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progressBar"></div>
                </div>
                <div class="progress-status" id="progressStatus">Processing file...</div>
                <div class="progress-steps" id="progressSteps"></div>
            </div>
            
            <div class="input-container">
                <label for="file" class="attachment-button" title="Upload a file">
                    <i class="fas fa-paperclip"></i>
                </label>
                <input type="file" id="file" accept=".csv,.json,.xml,.yaml,.yml,.xlsx,.xls" style="display: none;">
                <textarea id="query" placeholder="Ask a question about your data..." rows="1"></textarea>
                <button id="sendButton" disabled>Send</button>
            </div>
        </div>
        
        <script>
            let dataDictPath = null;
            let dbPath = null;
            let availableDatabases = [];
            // DOM elements
            const messagesContainer = document.getElementById('messages');
            const queryInput = document.getElementById('query');
            const sendButton = document.getElementById('sendButton');
            const fileInput = document.getElementById('file');
            const filePreview = document.getElementById('filePreview');
            const clearCacheButton = document.getElementById('clearCacheButton');
            const databaseSelect = document.getElementById('databaseSelect');
            
            // Function to add a user message
            function addUserMessage(message) {
                const messageElement = document.createElement('div');
                messageElement.className = 'message';
                messageElement.innerHTML = `
                    <div class="avatar user-avatar">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="content">
                        ${message}
                    </div>
                `;
                messagesContainer.appendChild(messageElement);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                return messageElement;
            }
            
            // Function to add a bot message
            function addBotMessage(content, isProgressMessage = false) {
                // Create message element
                const message = document.createElement('div');
                message.className = 'message';
                if (isProgressMessage) {
                    message.className += ' progress-message';
                }
                
                // Create avatar
                const avatar = document.createElement('div');
                avatar.className = 'avatar bot-avatar';
                
                // Use the same robot icon for all messages
                avatar.innerHTML = '<i class="fas fa-robot"></i>';
                
                // Create content
                const contentElement = document.createElement('div');
                contentElement.className = 'content';
                contentElement.innerHTML = content;
                
                // Append avatar and content to message
                message.appendChild(avatar);
                message.appendChild(contentElement);
                
                // Append message to messages container
                messagesContainer.appendChild(message);
                
                // Scroll to bottom
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            // Function to add a typing indicator
            function addTypingIndicator() {
                // Always create a new message with typing indicator at the end
                const indicator = document.createElement('div');
                indicator.className = 'message';
                indicator.id = 'typingIndicator';
                indicator.innerHTML = `
                    <div class="avatar bot-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="content">
                        <span class="typing-indicator">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </span>
                    </div>
                `;
                messagesContainer.appendChild(indicator);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                return indicator;
            }
            
            // Function to remove typing indicator
            function removeTypingIndicator() {
                const indicator = document.getElementById('typingIndicator');
                if (indicator) {
                    indicator.remove();
                }
            }
            
            // Function to handle file upload with progress tracking
            async function uploadFile(file) {
                try {
                    // Show typing indicator
                    addTypingIndicator();
                    
                    // Show progress container
                    const progressContainer = document.getElementById('progressContainer');
                    const progressBar = document.getElementById('progressBar');
                    const progressStatus = document.getElementById('progressStatus');
                    const progressSteps = document.getElementById('progressSteps');
                    
                    progressContainer.style.display = 'flex';
                    progressBar.style.width = '10%';
                    progressStatus.textContent = 'Uploading file...';
                    
                    // Initialize progress steps
                    const steps = [
                        { id: 'upload', text: 'Uploading file', status: 'active' },
                        { id: 'analyze', text: 'Analyzing file structure', status: 'pending' },
                        { id: 'schema', text: 'Processing schema', status: 'pending' },
                        { id: 'dictionary', text: 'Generating data dictionary', status: 'pending' },
                        { id: 'sample', text: 'Creating sample data', status: 'pending' },
                        { id: 'database', text: 'Setting up database', status: 'pending' }
                    ];
                    
                    // Render initial steps
                    function renderProgressSteps() {
                        progressSteps.innerHTML = '';
                        steps.forEach((step, index) => {
                            const stepElement = document.createElement('div');
                            stepElement.className = 'progress-step';
                            stepElement.innerHTML = `
                                <div class="step-indicator step-${step.status}">${index + 1}</div>
                                <div>${step.text}</div>
                            `;
                            progressSteps.appendChild(stepElement);
                        });
                    }
                    
                    function updateStep(stepId, status, progress) {
                        const stepIndex = steps.findIndex(s => s.id === stepId);
                        if (stepIndex >= 0) {
                            steps[stepIndex].status = status;
                            renderProgressSteps();
                            
                            // Update progress bar
                            if (progress) {
                                progressBar.style.width = `${progress}%`;
                            }
                        }
                    }
                    
                    renderProgressSteps();
                    
                    // Create form data
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    // Upload file
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`Server error: ${response.status} ${errorText}`);
                    }
                    
                    updateStep('upload', 'completed', 30);
                    updateStep('analyze', 'active', 40);
                    
                    // Process response
                    const result = await response.json();
                    
                    // Update progress for remaining steps
                    updateStep('analyze', 'completed', 60);
                    
                    if (result.is_schema_file) {
                        updateStep('schema', 'completed', 70);
                        updateStep('dictionary', 'completed', 80);
                        updateStep('sample', 'completed', 90);
                    }
                    
                    updateStep('database', 'completed', 100);
                    
                    // Hide progress after a short delay
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                    }, 2000);
                    
                    // Remove typing indicator
                    removeTypingIndicator();
                    
                    if (result.success) {
                        // Store paths for later use
                        dataDictPath = result.data_dict_path;
                        dbPath = result.db_path;
                        
                        // Add the new database to the available databases
                        const newDb = {
                            name: file.name,
                            path: result.db_path,
                            data_dict_path: result.data_dict_path
                        };
                        
                        // Add to available databases if not already present
                        if (!availableDatabases.some(db => db.path === newDb.path)) {
                            availableDatabases.push(newDb);
                            updateDatabaseSelector();
                        }
                        
                        // Add success message
                        let message = `<p><i class="fas fa-check-circle" style="color: var(--primary-color);"></i> File uploaded and processed successfully!</p>`;
                        
                        // Add analysis details
                        if (result.analysis) {
                            if (result.analysis.file_type) {
                                message += `<p>File type: <strong>${result.analysis.file_type}</strong></p>`;
                            }
                            
                            if (result.analysis.tables && result.analysis.tables.length > 0) {
                                message += `<p>Tables found: <strong>${result.analysis.tables.length}</strong></p>`;
                                message += `<ul>`;
                                result.analysis.tables.forEach(table => {
                                    message += `<li>${table.name} (${table.rows} rows, ${table.columns} columns)</li>`;
                                });
                                message += `</ul>`;
                            }
                            
                            if (result.is_schema_file) {
                                message += `<p><i class="fas fa-info-circle"></i> This is a schema file. Tables have been created with sample data.</p>`;
                            }
                        }
                        
                        message += `<p class="completion-message">You can now ask questions about your data!</p>`;
                        
                        addBotMessage(message);
                    } else {
                        throw new Error(result.error || 'Failed to process file');
                    }
                } catch (error) {
                    console.error('Error uploading file:', error);
                    removeTypingIndicator();
                    
                    // Hide progress container
                    document.getElementById('progressContainer').style.display = 'none';
                    
                    addBotMessage(`<p style="color: #ef4444;"><i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${error.message}</p>`);
                }
            }
            
            // Handle file input change
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    // Show file preview
                    filePreview.style.display = 'block';
                    filePreview.innerHTML = `
                        <div class="file-preview-content">
                            <i class="fas fa-file"></i>
                            <span>${file.name}</span>
                            <button class="remove-file" title="Remove file">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    `;
                    
                    // Add event listener to remove button
                    const removeButton = filePreview.querySelector('.remove-file');
                    removeButton.addEventListener('click', () => {
                        filePreview.style.display = 'none';
                        filePreview.innerHTML = '';
                        fileInput.value = '';
                        sendButton.disabled = !queryInput.value.trim();
                    });
                    
                    // Enable send button
                    sendButton.disabled = false;
                    
                    // Add user message
                    addUserMessage(`I'm uploading <strong>${file.name}</strong> for analysis.`);
                    
                    // Upload file
                    uploadFile(file);
                }
            });
            
            // Handle query input
            queryInput.addEventListener('input', () => {
                sendButton.disabled = !queryInput.value.trim() && !fileInput.files[0];
                
                // Auto-resize textarea
                queryInput.style.height = 'auto';
                queryInput.style.height = queryInput.scrollHeight + 'px';
            });
            
            // Handle send button click
            sendButton.addEventListener('click', () => {
                const query = queryInput.value.trim();
                
                if (query) {
                    // Add user message
                    addUserMessage(query);
                    
                    // Clear input
                    queryInput.value = '';
                    queryInput.style.height = 'auto';
                    sendButton.disabled = true;
                    
                    // Process query
                    processQuery(query);
                } else if (fileInput.files[0]) {
                    // If no query but file is selected, just upload the file
                    const file = fileInput.files[0];
                    
                    // Add user message
                    addUserMessage(`I'm uploading <strong>${file.name}</strong> for analysis.`);
                    
                    // Upload file
                    uploadFile(file);
                    
                    // Clear file input
                    fileInput.value = '';
                    filePreview.style.display = 'none';
                    filePreview.innerHTML = '';
                    sendButton.disabled = true;
                }
            });
            
            // Handle Enter key
            queryInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendButton.click();
                }
            });
            
            // Handle clear cache button click
            clearCacheButton.addEventListener('click', async () => {
                try {
                    // Show confirmation dialog
                    if (!confirm('Are you sure you want to clear all uploaded and generated files?')) {
                        return;
                    }
                    
                    // Show typing indicator
                    addTypingIndicator();
                    
                    // Call clear cache API
                    const response = await fetch('/api/clear_cache', {
                        method: 'POST'
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`Server error: ${response.status} ${errorText}`);
                    }
                    
                    const result = await response.json();
                    
                    // Remove typing indicator
                    removeTypingIndicator();
                    
                    if (result.success) {
                        // Reset global variables
                        dataDictPath = null;
                        dbPath = null;
                        availableDatabases = [];
                        
                        // Update database selector
                        updateDatabaseSelector();
                        
                        // Clear file preview
                        filePreview.style.display = 'none';
                        filePreview.innerHTML = '';
                        fileInput.value = '';
                        
                        // Disable send button
                        sendButton.disabled = !queryInput.value.trim();
                        
                        // Add success message
                        addBotMessage(`<p><i class="fas fa-check-circle" style="color: var(--primary-color);"></i> ${result.message}</p>`);
                    } else {
                        throw new Error(result.error || 'Failed to clear cache');
                    }
                } catch (error) {
                    console.error('Error clearing cache:', error);
                    removeTypingIndicator();
                    addBotMessage(`<p style="color: #ef4444;"><i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${error.message}</p>`);
                }
            });
            
            // Function to animate progress bar smoothly
            async function animateProgress(from, to, duration = 500) {
                const startTime = Date.now();
                const animate = () => {
                    const currentTime = Date.now();
                    const elapsedTime = currentTime - startTime;
                    const progress = Math.min(elapsedTime / duration, 1);
                    const currentValue = from + (to - from) * progress;
                    progressBar.style.width = `${currentValue}%`;
                    
                    if (progress < 1) {
                        requestAnimationFrame(animate);
                    }
                };
                animate();
                
                // Return a promise that resolves after the animation completes
                return new Promise(resolve => setTimeout(resolve, duration));
            }
            
            // Function to poll for agent activities
            let lastTimestamp = 0;
            let pollingInterval = null;
            let displayedEventIds = new Set(); // Track which events we've already displayed
            
            function pollAgentActivities() {
                console.log('Starting to poll for agent activities');
                
                // Clear any existing polling interval
                if (pollingInterval) {
                    clearInterval(pollingInterval);
                }
                
                // Reset tracking variables
                lastTimestamp = 0;
                displayedEventIds.clear();
                
                // Define the polling function
                async function fetchEvents() {
                    try {
                        console.log('Fetching agent events since:', lastTimestamp);
                        // Use the local proxy endpoint which forwards to the API server
                        const response = await fetch(`/api/events?since=${lastTimestamp}`);
                        if (!response.ok) {
                            console.error('Error fetching events:', response.status);
                            return;
                        }
                        
                        const data = await response.json();
                        console.log('Received events:', data.events.length);
                        
                        // Process each event
                        if (data.events && data.events.length > 0) {
                            // Sort events by timestamp
                            data.events.sort((a, b) => a.timestamp - b.timestamp);
                            
                            // Group events by agent for more compact display
                            const eventsByAgent = {};
                            const agentFinalStates = {};
                            
                            // First pass: group events by agent and find final states
                            data.events.forEach(eventData => {
                                const eventId = `${eventData.agent}-${eventData.workflow_state}-${eventData.message}`;
                                
                                // Skip if we've already displayed this exact event
                                if (displayedEventIds.has(eventId)) {
                                    return;
                                }
                                
                                // Group by agent
                                if (!eventsByAgent[eventData.agent]) {
                                    eventsByAgent[eventData.agent] = [];
                                }
                                
                                // Only store the event if it's a new workflow state for this agent
                                // or if it's the final state for this agent
                                const isNewState = !agentFinalStates[eventData.agent] || 
                                                 agentFinalStates[eventData.agent] !== eventData.workflow_state;
                                
                                // Update the final state for this agent
                                agentFinalStates[eventData.agent] = eventData.workflow_state;
                                
                                // Only add the event if it's a new state or the final message
                                if (isNewState) {
                                    eventsByAgent[eventData.agent].push({
                                        eventData,
                                        eventId
                                    });
                                }
                                
                                // Mark as displayed
                                displayedEventIds.add(eventId);
                            });
                            
                            // Second pass: display events grouped by agent
                            if (Object.keys(eventsByAgent).length > 0) {
                                console.log(`Displaying events for ${Object.keys(eventsByAgent).length} agents`);
                                
                                // Create a container for all agent events
                                let agentEvents = `<div class="agent-activities-container">`;
                                
                                // Add each agent's final state to the container
                                Object.keys(eventsByAgent).forEach(agent => {
                                    // Get the final event for this agent
                                    const events = eventsByAgent[agent];
                                    if (events.length === 0) return;
                                    
                                    const finalEvent = events[events.length - 1].eventData;
                                    agentEvents += `<p class="agent-activity"><strong>${finalEvent.agent}</strong> <span class="workflow-state">[${finalEvent.workflow_state}]</span>: ${finalEvent.message}</p>`;
                                });
                                
                                agentEvents += `</div>`;
                                
                                // Add all agent events as a single message
                                addBotMessage(agentEvents, true);
                            }
                                
                            // Update the last timestamp from the latest event
                            if (data.events.length > 0) {
                                const latestEvent = data.events[data.events.length - 1];
                                lastTimestamp = Math.max(lastTimestamp, latestEvent.timestamp);
                            }
                            
                            // Check if we're done
                            const lastEvent = data.events[data.events.length - 1];
                            if (lastEvent.workflow_state === 'DONE' || lastEvent.workflow_state === 'ERROR') {
                                console.log('Workflow complete, stopping polling');
                                clearInterval(pollingInterval);
                                pollingInterval = null;
                            }
                        }
                    } catch (error) {
                        console.error('Error polling agent activities:', error);
                    }
                }
                
                // Do an initial fetch
                fetchEvents();
                
                // Set up polling interval (every 500ms)
                pollingInterval = setInterval(fetchEvents, 500);
                
                return {
                    stop: function() {
                        if (pollingInterval) {
                            clearInterval(pollingInterval);
                            pollingInterval = null;
                        }
                    }
                };
            }
            
            // Function to upload file with progress tracking
            async function uploadFile(file) {
                try {
                    // Show typing indicator
                    addTypingIndicator();
                    
                    // Start polling for agent activities
                    const poller = pollAgentActivities();
                    
                    // Create form data
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    // Upload file
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        // Stop polling on error
                        poller.stop();
                        const errorText = await response.text();
                        throw new Error(`Server error: ${response.status} ${errorText}`);
                    }
                    
                    // Wait for the response to be parsed
                    const result = await response.json();
                    console.log('File upload response:', result);
                    
                    // Remove typing indicator
                    removeTypingIndicator();
                    
                    if (result.success) {
                        console.log('File upload successful, setting paths:', {
                            data_dict_path: result.data_dict_path,
                            db_path: result.db_path
                        });
                        
                        // Store paths for later use
                        dataDictPath = result.data_dict_path;
                        dbPath = result.db_path;
                        
                        console.log('Updated global paths:', { dataDictPath, dbPath });
                        
                        // Refresh the database list
                        await loadAvailableDatabases();
                        
                        // Add success message
                        let message = `<p><i class="fas fa-check-circle" style="color: var(--primary-color);"></i> File uploaded and processed successfully!</p>`;
                        
                        // Add analysis details
                        if (result.analysis) {
                            if (result.analysis.file_type) {
                                message += `<p>File type: <strong>${result.analysis.file_type}</strong></p>`;
                                message += `<p>${result.analysis.description || ''}</p>`;
                            }
                            
                            if (result.analysis.tables && result.analysis.tables.length > 0) {
                                message += `<p>Tables found: <strong>${result.analysis.tables.length}</strong></p>`;
                                message += `<ul>`;
                                result.analysis.tables.forEach(table => {
                                    message += `<li>${table.name} (${table.rows} rows, ${table.columns} columns)</li>`;
                                });
                                message += `</ul>`;
                            }
                            
                            if (result.is_schema_file) {
                                message += `<p><i class="fas fa-info-circle"></i> This is a schema file. Tables have been created with sample data.</p>`;
                            }
                            
                            // Don't display sample questions - they're redundant with agent events
                        }
                        
                        addBotMessage(message);
                        
                        // Enable send button for queries
                        sendButton.disabled = !queryInput.value.trim();
                    } else {
                        throw new Error(result.error || 'Failed to process file');
                    }
                } catch (error) {
                    console.error('Error uploading file:', error);
                    removeTypingIndicator();
                    
                    // Hide progress container
                    document.getElementById('progressContainer').style.display = 'none';
                    
                    addBotMessage(`<p style="color: #ef4444;"><i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${error.message}</p>`);
                }
            }
            
            // Function to process query
            async function processQuery(query) {
                try {
                    // Debug logging
                    console.log('Processing query with paths:', { dbPath, dataDictPath });
                    console.log('Available databases:', availableDatabases);
                    
                    // Check if we have stored paths in localStorage
                    const storedDbPath = localStorage.getItem('currentDbPath');
                    const storedDictPath = localStorage.getItem('currentDictPath');
                    
                    if (storedDbPath && storedDictPath) {
                        console.log('Found stored database paths in localStorage:', { storedDbPath, storedDictPath });
                        // Use stored paths if global variables are not set
                        if (!dbPath || !dataDictPath) {
                            dbPath = storedDbPath;
                            dataDictPath = storedDictPath;
                            console.log('Using stored paths from localStorage');
                        }
                    }
                    
                    // If no database is selected but we have available databases, select the first one
                    if ((!dbPath || !dataDictPath) && availableDatabases.length > 0) {
                        console.log('No database selected but databases are available, selecting first one');
                        dbPath = availableDatabases[0].path;
                        dataDictPath = availableDatabases[0].data_dict_path;
                        console.log('Auto-selected database for query:', { 
                            name: availableDatabases[0].name,
                            dbPath,
                            dataDictPath
                        });
                        
                        // Store the selection
                        localStorage.setItem('currentDbPath', dbPath);
                        localStorage.setItem('currentDictPath', dataDictPath);
                    }
                    
                    // Final check if database is ready
                    if (!dbPath || !dataDictPath) {
                        console.error('Database paths not set:', { dbPath, dataDictPath });
                        throw new Error('Please upload a data file first.');
                    }
                    
                    // Show typing indicator
                    addTypingIndicator();
                    
                    // Create the request payload with absolute paths
                    const payload = {
                        query: query,
                        db_path: dbPath,
                        data_dict_path: dataDictPath
                    };
                    
                    console.log('Sending query to API with payload:', payload);
                    
                    // Send query to API
                    const response = await fetch('/api/query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`Server error: ${response.status} ${errorText}`);
                    }
                    
                    const result = await response.json();
                    
                    // Remove typing indicator
                    removeTypingIndicator();
                    
                    if (result.success) {
                        // Build response HTML
                        let responseHtml = '';
                        
                        // Add summary if available
                        if (result.summary) {
                            responseHtml += `
                                <div style="margin-top: 0.5rem; padding: 0.75rem; background-color: rgba(16, 163, 127, 0.1); border-radius: 0.375rem; border-left: 3px solid var(--primary-color);">
                                    <p><strong><i class="fas fa-lightbulb"></i> Summary:</strong></p>
                                    <p>${result.summary}</p>
                                </div>
                            `;
                        }
                        
                        // Add reasoning if available
                        if (result.reasoning) {
                            responseHtml += `
                                <p><strong>Reasoning:</strong></p>
                                <p>${result.reasoning}</p>
                            `;
                        }
                        
                        // Add SQL query
                        responseHtml += `
                            <p style="margin-top: 0.5rem;"><strong>SQL Query:</strong></p>
                            <pre><code class="sql-code">${result.sql}</code></pre>
                        `;
                        
                        // Add results table if data is available
                        if (result.data && result.data.length > 0) {
                            responseHtml += `
                                <p style="margin-top: 0.5rem;"><strong>Results:</strong></p>
                                <div style="overflow-x: auto;">
                                    <table>
                                        <thead>
                                            <tr>
                            `;
                            
                            // Add table headers
                            result.columns.forEach(column => {
                                responseHtml += `<th>${column}</th>`;
                            });
                            
                            responseHtml += `
                                            </tr>
                                        </thead>
                                        <tbody>
                            `;
                            
                            // Add table rows
                            result.data.forEach(row => {
                                responseHtml += `<tr>`;
                                result.columns.forEach(column => {
                                    const value = row[column] !== null ? row[column] : '';
                                    responseHtml += `<td>${value}</td>`;
                                });
                                responseHtml += `</tr>`;
                            });
                            
                            responseHtml += `
                                        </tbody>
                                    </table>
                                </div>
                            `;
                        } else {
                            responseHtml += `
                                <p style="margin-top: 0.5rem;"><strong>No results found.</strong></p>
                            `;
                        }
                        
                        // Add bot message with response
                        addBotMessage(responseHtml);
                    } else {
                        throw new Error(result.error || 'Failed to process query');
                    }
                } catch (error) {
                    console.error('Error processing query:', error);
                    removeTypingIndicator();
                    addBotMessage(`<p style="color: #ef4444;"><i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${error.message}</p>`);
                }
                
                // Enable send button for next query
                sendButton.disabled = !queryInput.value.trim();
            }
            
            // Function to load available databases
            async function loadAvailableDatabases() {
                try {
                    console.log('Loading available databases...');
                    const response = await fetch('/api/list_databases');
                    
                    if (!response.ok) {
                        console.error('Failed to load databases');
                        return;
                    }
                    
                    const result = await response.json();
                    console.log('API response:', result);
                    
                    availableDatabases = result.databases || [];
                    console.log('Available databases:', availableDatabases);
                    
                    // Update the database selector UI
                    updateDatabaseSelector();
                    
                    // If we have databases but no current selection, select the first one
                    if (availableDatabases.length > 0) {
                        // If no database is currently selected, select the first one
                        if (!dbPath || !dataDictPath) {
                            dbPath = availableDatabases[0].path;
                            dataDictPath = availableDatabases[0].data_dict_path;
                            console.log('Auto-selected first database:', { 
                                name: availableDatabases[0].name,
                                dbPath,
                                dataDictPath
                            });
                            
                            // Add a message to indicate the database selection
                            addBotMessage(`<p><i class="fas fa-database"></i> Selected database: <strong>${availableDatabases[0].name}</strong></p>`);
                        } else {
                            console.log('Using existing database selection:', { dbPath, dataDictPath });
                        }
                    } else {
                        console.log('No databases available');
                        dbPath = null;
                        dataDictPath = null;
                    }
                } catch (error) {
                    console.error('Error loading databases:', error);
                }
            }
            
            // Function to update the database selector
            function updateDatabaseSelector() {
                console.log('Updating database selector with available databases:', availableDatabases);
                databaseSelect.innerHTML = '';
                
                if (availableDatabases.length === 0) {
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'No databases available';
                    option.disabled = true;
                    option.selected = true;
                    databaseSelect.appendChild(option);
                    databaseSelect.disabled = true;
                    dbPath = null;
                    dataDictPath = null;
                    console.log('No databases available, cleared paths');
                    return;
                }
                
                // Add options for each database
                availableDatabases.forEach(db => {
                    const option = document.createElement('option');
                    // Store the full database object as a data attribute
                    option.value = db.path;
                    
                    // Handle null data_dict_path - use an empty string instead
                    const dictPath = db.data_dict_path || '';
                    option.setAttribute('data-dict-path', dictPath);
                    option.textContent = db.name;
                    
                    // Check if this option should be selected
                    const isSelected = db.path === dbPath;
                    option.selected = isSelected;
                    
                    console.log(`Adding option: ${db.name}, path: ${db.path}, dict: ${dictPath}, selected: ${isSelected}`);
                    databaseSelect.appendChild(option);
                });
                
                // Always enable the dropdown if we have databases
                databaseSelect.disabled = false;
                console.log('Database selector enabled with', availableDatabases.length, 'options');
                
                // If no database was selected, select the first one
                if (!foundSelected && availableDatabases.length > 0) {
                    databaseSelect.options[0].selected = true;
                    dbPath = availableDatabases[0].path;
                    dataDictPath = availableDatabases[0].data_dict_path;
                }
                databaseSelect.disabled = false;
            }
            
            // Handle database selection change
            databaseSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const selectedDb = selectedOption.value;
                const selectedDictPath = selectedOption.getAttribute('data-dict-path');
                
                console.log('Database selection changed:', { 
                    value: selectedDb,
                    dictPath: selectedDictPath,
                    text: selectedOption.textContent 
                });
                
                if (selectedDb) {
                    // Find the selected database in the available databases
                    const db = availableDatabases.find(db => db.path === selectedDb);
                    console.log('Found database object:', db);
                    
                    if (db) {
                        // Update the global variables for query processing
                        dbPath = db.path;
                        dataDictPath = db.data_dict_path;
                        
                        console.log('Updated global paths:', { dbPath, dataDictPath });
                        
                        // Add a message to indicate the database change
                        addBotMessage(`<p><i class="fas fa-database"></i> Switched to database: <strong>${db.name}</strong></p>`);
                        
                        // Force synchronization with the backend
                        localStorage.setItem('currentDbPath', dbPath);
                        localStorage.setItem('currentDictPath', dataDictPath);
                    }
                }
            });
            
            // Load available databases on page load
            loadAvailableDatabases();
            
            // Auto-resize textarea on load
            queryInput.style.height = 'auto';
            queryInput.style.height = queryInput.scrollHeight + 'px';
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/upload', methods=['POST'])
def proxy_upload():
    """
    Proxy the file upload request to the API server.
    """
    import requests
    
    try:
        # Forward the file to the API server
        file = request.files['file']
        files = {'file': (file.filename, file.read(), file.content_type)}
        response = requests.post('http://localhost:5000/api/upload', files=files)
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

@app.route('/api/query', methods=['POST'])
def proxy_query():
    """
    Proxy the query request to the API server.
    """
    import requests
    
    try:
        # Forward the query to the API server
        data = request.json
        response = requests.post('http://localhost:5000/api/query', json=data)
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

@app.route('/api/clear_cache', methods=['POST'])
def proxy_clear_cache():
    """
    Proxy the clear cache request to the API server.
    """
    import requests
    
    try:
        # Forward the request to the API server
        response = requests.post('http://localhost:5000/api/clear_cache')
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

@app.route('/api/events', methods=['GET'])
def proxy_events():
    """
    Proxy the events request to the API server.
    """
    import requests
    
    try:
        # Get the since parameter if provided
        since = request.args.get('since', '0')
        
        # Forward the request to the API server
        response = requests.get(f'http://localhost:5000/api/events?since={since}')
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

@app.route('/api/list_databases', methods=['GET'])
def proxy_list_databases():
    """
    Proxy the list databases request to the API server.
    """
    import requests
    
    try:
        # Forward the request to the API server
        response = requests.get('http://localhost:5000/api/list_databases')
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
