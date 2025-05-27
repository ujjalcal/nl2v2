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
            justify-content: center;
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
            function addBotMessage(message) {
                const messageElement = document.createElement('div');
                messageElement.className = 'message';
                messageElement.innerHTML = `
                    <div class="avatar bot-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="content">
                        ${message}
                    </div>
                `;
                messagesContainer.appendChild(messageElement);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                return messageElement;
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
            
            // Function to upload file
            async function uploadFile(file) {
                try {
                    // Show typing indicator
                    addTypingIndicator();
                    
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
                    
                    const result = await response.json();
                    
                    // Remove typing indicator
                    removeTypingIndicator();
                    
                    if (result.success) {
                        // Store paths for later use
                        dataDictPath = result.data_dict_path;
                        dbPath = result.db_path;
                        
                        // Display analysis results
                        const analysis = result.analysis;
                        let analysisHtml = '';
                        
                        if (analysis.file_type) {
                            analysisHtml += `
                                <p>I've analyzed your file and detected it's a <strong>${analysis.file_type}</strong> file.</p>
                                <p style="margin-top: 0.5rem;">${analysis.description}</p>
                            `;
                            
                            if (analysis.key_fields && analysis.key_fields.length > 0) {
                                analysisHtml += `<p style="margin-top: 0.5rem;"><strong>Key fields:</strong></p><ul style="margin-left: 1.5rem;">`;
                                analysis.key_fields.forEach(field => {
                                    analysisHtml += `<li><strong>${field.name}</strong>: ${field.description}</li>`;
                                });
                                analysisHtml += `</ul>`;
                            }
                            
                            if (analysis.sample_questions && analysis.sample_questions.length > 0) {
                                analysisHtml += `
                                    <p style="margin-top: 0.5rem;"><strong>You can ask questions like:</strong></p>
                                    <ul style="margin-left: 1.5rem;">
                                `;
                                analysis.sample_questions.forEach(question => {
                                    analysisHtml += `<li>${question}</li>`;
                                });
                                analysisHtml += `</ul>`;
                            }
                        } else if (analysis.error) {
                            analysisHtml = `<p style="color: #ef4444;"><i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${analysis.error}</p>`;
                        }
                        
                        // Add processing steps
                        analysisHtml += `
                            <div style="margin-top: 1rem; border-left: 3px solid #8b5cf6; padding-left: 0.75rem; margin-bottom: 0.75rem;">
                                <p><i class="fas fa-database"></i> <strong>Setting up your database for querying...</strong></p>
                            </div>
                            
                            <div style="margin-top: 0.5rem;">
                                <p><strong>Processing Pipeline:</strong></p>
                                <div class="processing-step">
                                    <i class="fas fa-check-circle step-icon"></i>
                                    <span>File uploaded successfully</span>
                                </div>
                                <div class="processing-step">
                                    <i class="fas fa-check-circle step-icon"></i>
                                    <span>Data parsed and validated</span>
                                </div>
                                <div class="processing-step">
                                    <i class="fas fa-check-circle step-icon"></i>
                                    <span>Database created</span>
                                </div>
                                <div class="processing-step">
                                    <i class="fas fa-check-circle step-icon"></i>
                                    <span>Schema analyzed</span>
                                </div>
                                <div class="processing-step">
                                    <i class="fas fa-check-circle step-icon"></i>
                                    <span>Finalizing database</span>
                                </div>
                            </div>
                            
                            <div class="completion-message">
                                <p><i class="fas fa-check-circle"></i> <strong>Analysis complete!</strong> Your data is now ready for querying.</p>
                                <p style="margin-top: 0.25rem; font-size: 0.875rem;">You can now ask questions about your data using natural language.</p>
                            </div>
                        `;
                        
                        // Add bot message with analysis
                        addBotMessage(analysisHtml);
                        
                        // Enable send button for queries
                        sendButton.disabled = !queryInput.value.trim();
                    } else {
                        throw new Error(result.error || 'Failed to process file');
                    }
                } catch (error) {
                    console.error('Error uploading file:', error);
                    removeTypingIndicator();
                    addBotMessage(`<p style="color: #ef4444;"><i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${error.message}</p>`);
                }
            }
            
            // Function to process query
            async function processQuery(query) {
                try {
                    // Check if database is ready
                    if (!dbPath || !dataDictPath) {
                        throw new Error('Please upload a file first');
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
