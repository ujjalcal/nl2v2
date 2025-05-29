from flask import Flask, render_template_string, request
from flask_cors import CORS
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app)

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
            display: none;
        }
        
        .file-preview {
            display: none;
            margin-top: 0.5rem;
            padding: 0.5rem;
            background-color: #f3f4f6;
            border-radius: 0.375rem;
            font-size: 0.875rem;
        }
        
        .file-preview-content {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .remove-file {
            background-color: transparent;
            border: none;
            color: var(--secondary-text-color);
            cursor: pointer;
            padding: 0.25rem;
            font-size: 0.75rem;
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
            <h1>NL2SQL Tool</h1>
            <button id="clearCacheButton" class="clear-cache-button" title="Clear all uploaded and generated files">
                <i class="fas fa-trash"></i>
            </button>
        </div>
        
        <div class="chat-container">
            <div class="messages" id="messages">
                <!-- Welcome message -->
                <div class="message">
                    <div class="avatar bot-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="content">
                        <p>Hi, I'm your NL2SQL assistant. I can help you analyze data files and convert your natural language questions into SQL queries.</p>
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
                <input type="file" id="file" accept=".csv,.json,.xml,.yaml,.yml,.xlsx,.xls">
                <textarea id="query" placeholder="Ask a question about your data..." rows="1"></textarea>
                <button id="sendButton" disabled>Send</button>
            </div>
        </div>
        
        <script>
            let dataDictPath = null;
            let dbPath = null;
            const messagesContainer = document.getElementById('messages');
            const queryInput = document.getElementById('query');
            const sendButton = document.getElementById('sendButton');
            const fileInput = document.getElementById('file');
            const filePreview = document.getElementById('filePreview');
            const clearCacheButton = document.getElementById('clearCacheButton');
            
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
                
                // Use different icon for progress messages
                if (isProgressMessage) {
                    avatar.innerHTML = '<i class="fas fa-cog fa-spin"></i>';
                } else {
                    avatar.innerHTML = '<i class="fas fa-robot"></i>';
                }
                
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
            
            function pollAgentActivities() {
                console.log('Starting to poll for agent activities');
                
                // Clear any existing polling interval
                if (pollingInterval) {
                    clearInterval(pollingInterval);
                }
                
                // Reset timestamp to get all events
                lastTimestamp = 0;
                
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
                            
                            // Display each event
                            data.events.forEach(eventData => {
                                console.log('Displaying agent event:', eventData.agent, eventData.workflow_state, eventData.message);
                                
                                // Create a message showing which agent is active, the workflow state, and what it's doing
                                const statusMessage = `<p><strong>${eventData.agent}</strong> <span class="workflow-state">[${eventData.workflow_state}]</span>: ${eventData.message}</p>`;
                                addBotMessage(statusMessage, true); // true means this is a progress message
                                
                                // Update the last timestamp
                                lastTimestamp = Math.max(lastTimestamp, eventData.timestamp);
                            });
                            
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
                    
                    // Add initial message about file upload
                    addBotMessage(`<p><strong>WorkflowOrchestratorAgent</strong> <span class="workflow-state">[INITIALIZING]</span>: Starting to process file: ${file.name}</p>`, true);
                    
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
                    
                    // Note: We don't need to stop the poller here as it will
                    // automatically stop when the workflow reaches DONE or ERROR state
                    
                    // Remove typing indicator
                    removeTypingIndicator();
                    
                    if (result.success) {
                        // Store paths for later use
                        dataDictPath = result.data_dict_path;
                        dbPath = result.db_path;
                        
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
                            
                            if (result.analysis.sample_questions && result.analysis.sample_questions.length > 0) {
                                message += `<p><strong>You can ask questions like:</strong></p><ul>`;
                                result.analysis.sample_questions.forEach(question => {
                                    message += `<li>${question}</li>`;
                                });
                                message += `</ul>`;
                            }
                        }
                        
                        message += `<p class="completion-message">You can now ask questions about your data!</p>`;
                        
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
                    // Check if database is ready
                    if (!dbPath || !dataDictPath) {
                        throw new Error('Please upload a data file first.');
                    }
                    
                    // Show typing indicator
                    addTypingIndicator();
                    
                    // Send query to API
                    const response = await fetch('/api/query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            query: query,
                            db_path: dbPath,
                            data_dict_path: dataDictPath
                        })
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
