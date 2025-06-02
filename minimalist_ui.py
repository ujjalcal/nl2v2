from flask import Flask, render_template_string, request, Response
from flask_cors import CORS
import os
import json
import requests

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
        
        .header-buttons {
            display: flex;
            gap: 0.5rem;
        }
        
        .view-goals-button {
            background-color: transparent;
            color: #6b7280;
            border: none;
            cursor: pointer;
            padding: 0.5rem;
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            transition: color 0.2s;
        }
        
        .view-goals-button:hover {
            color: var(--primary-color);
        }
        
        /* Goals modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            overflow: auto;
        }
        
        .modal-content {
            background-color: white;
            margin: 10% auto;
            padding: 1.5rem;
            border-radius: 0.5rem;
            width: 80%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        }
        
        .close-button {
            position: absolute;
            top: 1rem;
            right: 1rem;
            font-size: 1.5rem;
            cursor: pointer;
            color: #6b7280;
        }
        
        .close-button:hover {
            color: #ef4444;
        }
        
        /* Goal styles */
        .goals-list {
            margin-top: 1rem;
        }
        
        .goal-item {
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
            transition: all 0.2s ease;
        }
        
        .goal-item:hover {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .goal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .goal-title {
            font-weight: 600;
            font-size: 1.1rem;
        }
        
        .goal-status {
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .status-pending {
            background-color: #f3f4f6;
            color: #6b7280;
        }
        
        .status-in-progress {
            background-color: #eff6ff;
            color: #3b82f6;
        }
        
        .status-completed {
            background-color: #ecfdf5;
            color: #10b981;
        }
        
        .status-failed {
            background-color: #fef2f2;
            color: #ef4444;
        }
        
        .goal-details {
            margin-top: 0.5rem;
            font-size: 0.9rem;
        }
        
        .goal-description {
            color: var(--secondary-text-color);
            margin-bottom: 0.5rem;
        }
        
        .subgoals-list {
            margin-left: 1.5rem;
            margin-top: 0.5rem;
        }
        
        .view-details-btn {
            background-color: #f9fafb;
            border: 1px solid var(--border-color);
            border-radius: 0.25rem;
            padding: 0.25rem 0.5rem;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-top: 0.5rem;
        }
        
        .view-details-btn:hover {
            background-color: #f3f4f6;
            border-color: #d1d5db;
        }
        
        .goal-detail-view {
            padding: 1rem;
        }
        
        .goal-detail-view h3 {
            margin-bottom: 0.5rem;
            font-size: 1.2rem;
        }
        
        .goal-detail-view h4 {
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            font-size: 1rem;
            color: var(--text-color);
        }
        
        .reasoning-steps {
            margin-left: 1.5rem;
            margin-top: 0.5rem;
            color: var(--secondary-text-color);
            padding-left: 1rem;
            border-left: 2px solid #e5e7eb;
        }
        
        .reasoning-step {
            margin-bottom: 0.25rem;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        
        .goal-result {
            margin-top: 0.5rem;
            padding: 0.5rem;
            background-color: #f9fafb;
            border-radius: 0.25rem;
            font-size: 0.9rem;
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
        
        /* Goals modal styles */
        .goals-modal {
            display: none;
            position: fixed;
            z-index: 1;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.4);
        }
        
        .goals-modal-content {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
        }
        
        .goals-modal-content .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
        }
        
        .goals-modal-content .close:hover,
        .goals-modal-content .close:focus {
            color: black;
            text-decoration: none;
            cursor: pointer;
        }
        
        .goal-item {
            margin-bottom: 1rem;
        }
        
        .goal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        
        .goal-title {
            font-weight: 600;
        }
        
        .goal-status {
            font-size: 0.875rem;
            color: #666;
        }
        
        .status-pending {
            color: #666;
        }
        
        .status-in-progress {
            color: #0d8c6d;
        }
        
        .status-completed {
            color: #34c759;
        }
        
        .status-failed {
            color: #ef4444;
        }
        
        .reasoning-steps {
            margin-top: 1rem;
        }
        
        .reasoning-step {
            margin-bottom: 0.5rem;
        }
        
        .subgoals {
            margin-top: 1rem;
        }
        
        .subgoals-list {
            margin-top: 0.5rem;
        }
        
        .goal-result {
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <button id="clearCacheButton" class="clear-cache-button">
            <i class="fas fa-trash"></i> Clear Cache
        </button>
        <h1>NL2SQL Tool</h1>
        <div class="header-buttons">
            <button id="viewGoalsButton" class="view-goals-button">
                <i class="fas fa-tasks"></i> View Goals
            </button>
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
    
    <!-- Goals modal -->
    <div id="goalsModal" class="modal">
        <div class="modal-content">
            <span class="close-button" id="closeGoalsModal">&times;</span>
            <h2>Goals</h2>
            <div id="goalsList" class="goals-list"></div>
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
        
        // Goals modal
        const goalsModal = document.getElementById('goalsModal');
        const viewGoalsButton = document.getElementById('viewGoalsButton');
        const closeGoalsModal = document.getElementById('closeGoalsModal');
        const goalsList = document.getElementById('goalsList');
        
        viewGoalsButton.addEventListener('click', async () => {
            goalsModal.style.display = 'block';
            await loadGoals();
        });
        
        closeGoalsModal.addEventListener('click', () => {
            goalsModal.style.display = 'none';
        });
        
        window.addEventListener('click', (event) => {
            if (event.target === goalsModal) {
                goalsModal.style.display = 'none';
            }
        });
        
        async function loadGoals() {
            try {
                const response = await fetch('/api/goals');
                const result = await response.json();
                
                if (result.success && result.goals) {
                    if (result.goals.length === 0) {
                        goalsList.innerHTML = '<p>No goals found.</p>';
                        return;
                    }
                    
                    let goalsHtml = '';
                    for (const goal of result.goals) {
                        const statusClass = getStatusClass(goal.status);
                        
                        goalsHtml += `
                            <div class="goal-item" data-goal-id="${goal.id}">
                                <div class="goal-header">
                                    <div class="goal-title">${goal.name}</div>
                                    <div class="goal-status ${statusClass}">${goal.status}</div>
                                </div>
                                <div class="goal-details">
                                    <div class="goal-description">${goal.description}</div>
                                    <button class="view-details-btn">View Details</button>
                                </div>
                            </div>
                        `;
                    }
                    
                    goalsList.innerHTML = goalsHtml;
                    
                    // Add event listeners to view details buttons
                    const detailButtons = document.querySelectorAll('.view-details-btn');
                    detailButtons.forEach(button => {
                        button.addEventListener('click', async (e) => {
                            const goalItem = e.target.closest('.goal-item');
                            const goalId = goalItem.dataset.goalId;
                            await viewGoalDetails(goalId);
                        });
                    });
                } else {
                    goalsList.innerHTML = '<p>Error loading goals.</p>';
                }
            } catch (error) {
                console.error('Error loading goals:', error);
                goalsList.innerHTML = `<p>Error loading goals: ${error.message}</p>`;
            }
        }
        
        // Helper function to get status class
        function getStatusClass(status) {
            switch (status.toLowerCase()) {
                case 'pending':
                    return 'status-pending';
                case 'in progress':
                    return 'status-in-progress';
                case 'completed':
                    return 'status-completed';
                case 'failed':
                    return 'status-failed';
                default:
                    return 'status-pending';
            }
        }
        
        // Function to view goal details
        async function viewGoalDetails(goalId) {
            try {
                const response = await fetch(`/api/goals/${goalId}`);
                const result = await response.json();
                
                if (result.success && result.goal) {
                    const goal = result.goal;
                    const statusClass = getStatusClass(goal.status);
                    
                    let detailsHtml = `
                        <div class="goal-detail-view">
                            <h3>${goal.name}</h3>
                            <div class="goal-status ${statusClass}">${goal.status}</div>
                            <p class="goal-description">${goal.description}</p>
                    `;
                    
                    // Add reasoning steps if available
                    if (goal.reasoning_steps && goal.reasoning_steps.length > 0) {
                        detailsHtml += `<h4>Reasoning Steps:</h4><ol class="reasoning-steps">`;
                        goal.reasoning_steps.forEach(step => {
                            detailsHtml += `<li>${step}</li>`;
                        });
                        detailsHtml += `</ol>`;
                    }
                    
                    // Add subgoals if available
                    if (goal.subgoals && goal.subgoals.length > 0) {
                        detailsHtml += `<h4>Subgoals:</h4><div class="subgoals-list">`;
                        goal.subgoals.forEach(subgoal => {
                            const subgoalStatusClass = getStatusClass(subgoal.status);
                            detailsHtml += `
                                <div class="subgoal-item">
                                    <div class="subgoal-header">
                                        <div class="subgoal-title">${subgoal.name}</div>
                                        <div class="goal-status ${subgoalStatusClass}">${subgoal.status}</div>
                                    </div>
                                    <div class="subgoal-description">${subgoal.description}</div>
                                </div>
                            `;
                        });
                        detailsHtml += `</div>`;
                    }
                    
                    // Add result if available
                    if (goal.result) {
                        detailsHtml += `
                            <h4>Result:</h4>
                            <div class="goal-result">
                                <pre>${JSON.stringify(goal.result, null, 2)}</pre>
                            </div>
                        `;
                    }
                    
                    // Add execute button if goal is pending
                    if (goal.status.toLowerCase() === 'pending') {
                        detailsHtml += `
                            <div class="goal-actions">
                                <button id="executeGoalBtn" data-goal-id="${goal.id}" class="execute-goal-btn">Execute Goal</button>
                            </div>
                        `;
                    }
                    
                    detailsHtml += `</div>`;
                    
                    // Create a modal for the details
                    const detailsModal = document.createElement('div');
                    detailsModal.className = 'modal';
                    detailsModal.style.display = 'block';
                    detailsModal.innerHTML = `
                        <div class="modal-content">
                            <span class="close-button">&times;</span>
                            ${detailsHtml}
                        </div>
                    `;
                    
                    document.body.appendChild(detailsModal);
                    
                    // Add close button event listener
                    const closeButton = detailsModal.querySelector('.close-button');
                    closeButton.addEventListener('click', () => {
                        document.body.removeChild(detailsModal);
                    });
                    
                    // Add click outside to close
                    detailsModal.addEventListener('click', (event) => {
                        if (event.target === detailsModal) {
                            document.body.removeChild(detailsModal);
                        }
                    });
                    
                    // Add execute button event listener if present
                    const executeBtn = detailsModal.querySelector('#executeGoalBtn');
                    if (executeBtn) {
                        executeBtn.addEventListener('click', async () => {
                            await executeGoal(goal.id);
                            document.body.removeChild(detailsModal);
                            // Refresh goals list
                            await loadGoals();
                        });
                    }
                } else {
                    alert('Error loading goal details.');
                }
            } catch (error) {
                console.error('Error viewing goal details:', error);
                alert(`Error viewing goal details: ${error.message}`);
            }
        }
        
        // Function to execute a goal
        async function executeGoal(goalId) {
            try {
                const response = await fetch(`/api/goals/${goalId}/execute`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Start polling for agent activities
                    pollAgentActivities();
                    return true;
                } else {
                    alert(`Error executing goal: ${result.error || 'Unknown error'}`);
                    return false;
                }
            } catch (error) {
                console.error('Error executing goal:', error);
                alert(`Error executing goal: ${error.message}`);
                return false;
            }
        }
        
        // Function to animate progress bar
        function animateProgressBar(progressBar, from, to, duration = 500) {
            const startTime = performance.now();
            
            const animate = () => {
                const currentTime = performance.now();
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
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
    try:
        # Get API port from environment or default to 5000
        api_port = os.environ.get('API_PORT', '5000')
        
        # Forward the file to the API server
        file = request.files['file']
        files = {'file': (file.filename, file.read(), file.content_type)}
        response = requests.post(f'http://localhost:{api_port}/api/upload', files=files)
        
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
    try:
        # Get API port from environment or default to 5000
        api_port = os.environ.get('API_PORT', '5000')
        
        # Forward the query to the API server
        data = request.json
        response = requests.post(f'http://localhost:{api_port}/api/query', json=data)
        
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
    try:
        # Get API port from environment or default to 5000
        api_port = os.environ.get('API_PORT', '5000')
        
        # Forward the request to the API server
        response = requests.post(f'http://localhost:{api_port}/api/clear_cache')
        
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
    try:
        # Get API port from environment or default to 5000
        api_port = os.environ.get('API_PORT', '5000')
        
        # Get the since parameter if provided
        since = request.args.get('since', '0')
        
        # Forward the request to the API server
        response = requests.get(f'http://localhost:{api_port}/api/events?since={since}')
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

@app.route('/api/goals', methods=['GET'])
def proxy_goals():
    """
    Proxy the goals request to the API server.
    """
    try:
        # Get API port from environment or default to 5000
        api_port = os.environ.get('API_PORT', '5000')
        
        # Forward the request to the API server
        response = requests.get(f'http://localhost:{api_port}/api/goals')
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

@app.route('/api/goals/<goal_id>', methods=['GET'])
def proxy_goal(goal_id):
    """
    Proxy the goal request to the API server.
    """
    try:
        # Get API port from environment or default to 5000
        api_port = os.environ.get('API_PORT', '5000')
        
        # Forward the request to the API server
        response = requests.get(f'http://localhost:{api_port}/api/goals/{goal_id}')
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

@app.route('/api/goals', methods=['POST'])
def proxy_create_goal():
    """
    Proxy the create goal request to the API server.
    """
    try:
        # Get API port from environment or default to 5000
        api_port = os.environ.get('API_PORT', '5000')
        
        # Forward the request to the API server
        data = request.json
        response = requests.post(f'http://localhost:{api_port}/api/goals', json=data)
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

@app.route('/api/goals/<goal_id>/execute', methods=['POST'])
def proxy_execute_goal(goal_id):
    """
    Proxy the execute goal request to the API server.
    """
    try:
        # Get API port from environment or default to 5000
        api_port = os.environ.get('API_PORT', '5000')
        
        # Forward the request to the API server
        data = request.json
        response = requests.post(f'http://localhost:{api_port}/api/goals/{goal_id}/execute', json=data)
        
        # Return the API response
        return response.content, response.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        return {
            'error': f'Error forwarding request to API server: {str(e)}'
        }, 500

if __name__ == '__main__':
    # Get UI port from environment or default to 8501
    ui_port = int(os.environ.get('UI_PORT', '8501'))
    app.run(debug=True, port=ui_port)
