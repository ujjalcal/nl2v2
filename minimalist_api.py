import os
import json
import pandas as pd
import numpy as np
import sqlite3
import openai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from data_preplanner import DataPreplanner
from agentic_processor import AgenticQueryProcessor

# Custom JSON encoder to handle NaN values
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Series):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super(NpEncoder, self).default(obj)

# Initialize Flask app
app = Flask(__name__, static_folder='frontend/build')
# Enable CORS with specific settings
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Configure folder structure
# Main temp folder for all uploads and generated files
TEMP_FOLDER = 'temp'
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

# Upload folder for storing uploaded files
UPLOAD_FOLDER = os.path.join(TEMP_FOLDER, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Gen folder for storing dictionaries and databases
GEN_FOLDER = os.path.join(TEMP_FOLDER, 'gen')
if not os.path.exists(GEN_FOLDER):
    os.makedirs(GEN_FOLDER)

# Data dictionary folder inside gen folder
DATA_DICT_FOLDER = os.path.join(GEN_FOLDER, 'dictionaries')
if not os.path.exists(DATA_DICT_FOLDER):
    os.makedirs(DATA_DICT_FOLDER)

# Global processor instance
processor = None

def analyze_file_with_llm(file_path):
    """Use GPT to analyze the file content and determine if it's a schema or data"""
    try:
        # Read a sample of the file (first 10 lines)
        with open(file_path, 'r', encoding='utf-8') as f:
            sample_content = ''.join([next(f) for _ in range(10) if f])
        
        # Create a prompt for GPT
        prompt = f"""Analyze the following file content and determine if it contains schema information or actual data.
        File content sample:
        {sample_content}
        
        Please respond with a JSON object containing the following fields:
        1. file_type: 'schema' or 'data'
        2. description: A brief description of what the file contains
        3. recommendation: How to process this file (e.g., 'Create database tables', 'Import as data')
        """
        
        # Query GPT
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes file content to determine if it contains schema information or actual data."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=500
        )
        
        # Parse the response
        analysis = json.loads(response.choices[0].message.content)
        print(f"File analysis: {analysis}")
        
        return analysis
    except Exception as e:
        print(f"Error analyzing file with LLM: {str(e)}")
        return {
            "file_type": "unknown",
            "description": f"Error analyzing file: {str(e)}",
            "recommendation": "Process as regular data file"
        }

@app.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    """Clear all cached files in the temp folder"""
    try:
        # Reset the global processor first to release any database connections
        global processor
        processor = None
        
        files_cleared = 0
        files_skipped = 0
        
        # Clear uploads folder
        for file in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    files_cleared += 1
                except PermissionError:
                    # Skip files that are in use
                    print(f"Skipping file in use: {file_path}")
                    files_skipped += 1
                
        # Clear dictionaries folder
        for file in os.listdir(DATA_DICT_FOLDER):
            file_path = os.path.join(DATA_DICT_FOLDER, file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    files_cleared += 1
                except PermissionError:
                    # Skip files that are in use
                    print(f"Skipping file in use: {file_path}")
                    files_skipped += 1
                
        # Clear database files in gen folder
        for file in os.listdir(GEN_FOLDER):
            if file.endswith('.db'):
                file_path = os.path.join(GEN_FOLDER, file)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        files_cleared += 1
                    except PermissionError:
                        # Skip files that are in use
                        print(f"Skipping file in use: {file_path}")
                        files_skipped += 1
        
        message = f"Cache cleared successfully. {files_cleared} files removed"
        if files_skipped > 0:
            message += f", {files_skipped} files skipped (in use)"
        
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        print(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads and process them"""
    if 'file' not in request.files:
        response = json.dumps({'error': 'No file part'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    file = request.files['file']
    if file.filename == '':
        response = json.dumps({'error': 'No selected file'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    # Create upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # Save the uploaded file
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    # Get file extension
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Use LLM to analyze the file content
    file_analysis = analyze_file_with_llm(file_path)
    
    # Process the file based on LLM analysis and file type
    try:
        # Read the file into a DataFrame based on its extension
        if file_ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        elif file_ext == '.json':
            df = pd.read_json(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_ext == '.xml':
            import xml.etree.ElementTree as ET
            # Parse XML to DataFrame
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract data from XML
            data = []
            for child in root:
                row = {}
                for subchild in child:
                    row[subchild.tag] = subchild.text
                data.append(row)
            
            df = pd.DataFrame(data)
        elif file_ext in ['.yaml', '.yml']:
            import yaml
            # Parse YAML to DataFrame
            with open(file_path, 'r') as yaml_file:
                yaml_data = yaml.safe_load(yaml_file)
            
            # Handle different YAML structures
            if isinstance(yaml_data, list):
                # List of dictionaries
                df = pd.DataFrame(yaml_data)
            elif isinstance(yaml_data, dict):
                # Single dictionary or nested structure
                # Try to flatten if it's a nested structure
                if all(isinstance(v, dict) for v in yaml_data.values()):
                    # It's a nested dictionary, each key is an entry
                    records = []
                    for key, value in yaml_data.items():
                        record = {'id': key}
                        record.update(value)
                        records.append(record)
                    df = pd.DataFrame(records)
                else:
                    # It's a single dictionary, convert to a single row DataFrame
                    df = pd.DataFrame([yaml_data])
            else:
                raise ValueError("Unsupported YAML structure")
        else:
            response = json.dumps({'error': f'Unsupported file format: {file_ext}'}, cls=NpEncoder)
            return response, 400, {'Content-Type': 'application/json'}
        
        # Replace NaN values with None in the DataFrame
        df = df.replace({np.nan: None})
        
        # Get basic stats
        stats = {
            'rows': int(len(df)),
            'columns': int(len(df.columns)),
            'data_types': int(len(df.dtypes.unique())),
            'preview': df.head(5).to_dict(orient='records')
        }
        
        # Add LLM analysis to the response
        response_data = {
            'success': True,
            'file_path': file_path,
            'stats': stats,
            'analysis': file_analysis
        }
        
        # Use custom JSON encoder to handle NaN values
        response = json.dumps(response_data, cls=NpEncoder)
        
        return response, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        response = json.dumps({'error': str(e)}, cls=NpEncoder)
        return response, 500, {'Content-Type': 'application/json'}

@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    """Analyze a data file and generate an enriched data dictionary"""
    data = request.json
    file_path = data.get('file_path')
    file_analysis = data.get('analysis', {})
    
    if not file_path or not os.path.exists(file_path):
        response = json.dumps({'error': 'Invalid file path'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    try:
        # Create data dictionary folder if it doesn't exist
        if not os.path.exists(DATA_DICT_FOLDER):
            os.makedirs(DATA_DICT_FOLDER)
        
        # If no analysis was provided, perform it now
        if not file_analysis:
            file_analysis = analyze_file_with_llm(file_path)
        
        # Process data file based on analysis
        analyzer = DataPreplanner()
        
        # If the file is a schema, use a different approach
        is_schema = file_analysis.get('file_type') == 'schema'
        
        if is_schema:
            print(f"Processing schema file: {file_path}")
            # For schema files, we'll use a different approach
            # The data dictionary will be derived directly from the schema
            data_dict = analyzer.analyze_schema(file_path)
        else:
            # For regular data files, use the standard approach
            data_dict = analyzer.analyze_data(file_path)
        
        # Save data dictionary
        dataset_name = os.path.basename(file_path).split('.')[0]
        data_dict_path = os.path.join(DATA_DICT_FOLDER, f"{dataset_name}_data_dict.json")
        analyzer.save_data_dictionary(data_dict, data_dict_path, format="json")
        
        # Create SQLite database in the gen folder
        db_path = os.path.join(GEN_FOLDER, f"{dataset_name}.db")
        create_database_from_file(file_path, db_path)
        
        # Use custom JSON encoder to handle NaN values
        response = json.dumps({
            'success': True,
            'data_dict_path': data_dict_path,
            'db_path': db_path,
            'data_dict': data_dict,
            'analysis': file_analysis
        }, cls=NpEncoder)
        
        return response, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        print(f"Error analyzing data: {str(e)}")
        response = json.dumps({'error': str(e)}, cls=NpEncoder)
        return response, 500, {'Content-Type': 'application/json'}

@app.route('/api/process_query', methods=['POST'])
def process_query():
    """Process a natural language query using the agentic approach"""
    global processor
    
    data = request.json
    query = data.get('query')
    data_dict_path = data.get('data_dict_path')
    db_path = data.get('db_path')
    
    if not query:
        response = json.dumps({'error': 'No query provided'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    if not data_dict_path or not db_path:
        response = json.dumps({'error': 'Data dictionary or database path not provided'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    try:
        # Initialize processor if needed
        if processor is None:
            processor = AgenticQueryProcessor(
                data_dict_path=data_dict_path,
                db_path=db_path
            )
        
        # Process the query
        result = processor.process_query(query)
        
        # Make sure result is a dictionary
        if isinstance(result, str):
            result = {'sql_query': result, 'results': [], 'reasoning': 'Direct SQL query', 'execution_plan': result}
        
        # Convert DataFrame results to lists of dictionaries
        if isinstance(result.get('results'), pd.DataFrame):
            result['results'] = result['results'].to_dict(orient='records')
        
        # Use custom JSON encoder to handle NaN values
        response = json.dumps({
            'success': True,
            'result': result
        }, cls=NpEncoder)
        
        return response, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        response = json.dumps({'error': str(e)}, cls=NpEncoder)
        return response, 500, {'Content-Type': 'application/json'}

def create_database_from_file(file_path, db_path):
    """Create a SQLite database from a data file"""
    # Get file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Read file based on extension
    if file_ext == '.csv':
        df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
    elif file_ext == '.json':
        df = pd.read_json(file_path)
    elif file_ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
    elif file_ext == '.xml':
        import xml.etree.ElementTree as ET
        # Parse XML to DataFrame
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract data from XML
        data = []
        for child in root:
            row = {}
            for subchild in child:
                row[subchild.tag] = subchild.text
            data.append(row)
        
        df = pd.DataFrame(data)
    elif file_ext in ['.yaml', '.yml']:
        import yaml
        # Parse YAML to DataFrame
        with open(file_path, 'r') as yaml_file:
            yaml_data = yaml.safe_load(yaml_file)
        
        # Handle different YAML structures
        if isinstance(yaml_data, list):
            # List of dictionaries
            df = pd.DataFrame(yaml_data)
        elif isinstance(yaml_data, dict):
            # Single dictionary or nested structure
            # Try to flatten if it's a nested structure
            if all(isinstance(v, dict) for v in yaml_data.values()):
                # It's a nested dictionary, each key is an entry
                records = []
                for key, value in yaml_data.items():
                    record = {'id': key}
                    record.update(value)
                    records.append(record)
                df = pd.DataFrame(records)
            else:
                # It's a single dictionary, convert to a single row DataFrame
                df = pd.DataFrame([yaml_data])
        else:
            raise ValueError("Unsupported YAML structure")
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")
    
    # Replace NaN values with None to avoid JSON serialization issues
    df = df.replace({np.nan: None})
    
    # Create SQLite database
    conn = sqlite3.connect(db_path)
    
    # Get table name from file name
    table_name = os.path.basename(file_path).split('.')[0]
    
    # Write DataFrame to SQLite
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    # Close connection
    conn.close()
    
    return db_path

# Serve a simple HTML interface at the root URL
@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NL2SQL Tool</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #374151;
            --primary-color: #10a37f;
            --secondary-color: #f9fafb;
            --border-color: #e5e7eb;
            --hover-color: #f3f4f6;
            --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            --radius: 0.375rem;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.5;
            height: 100vh;
            display: flex;
            flex-direction: column;
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
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-color);
        }
        
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 800px;
            margin: 0 auto;
            width: 100%;
            height: calc(100vh - 130px);
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        .message {
            display: flex;
            gap: 1rem;
            padding: 0.5rem 0;
            max-width: 100%;
        }
        
        .avatar {
            width: 28px;
            height: 28px;
            border-radius: 0.25rem;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        
        .user-avatar {
            background-color: #c084fc;
            color: white;
        }
        
        .bot-avatar {
            background-color: var(--primary-color);
            color: white;
        }
        
        .content {
            flex: 1;
            padding-top: 0.25rem;
            overflow-wrap: break-word;
        }
        
        .welcome-message {
            text-align: center;
            padding: 2rem;
            color: #6b7280;
        }
        
        .input-area {
            border-top: 1px solid var(--border-color);
            padding: 1rem;
            position: relative;
        }
        
        .input-container {
            display: flex;
            border: 1px solid var(--border-color);
            border-radius: var(--radius);
            background-color: var(--bg-color);
            overflow: hidden;
            box-shadow: var(--shadow);
        }
        
        .input-field {
            flex: 1;
            border: none;
            padding: 0.75rem 1rem;
            font-size: 0.875rem;
            outline: none;
            resize: none;
            max-height: 200px;
            min-height: 24px;
            overflow-y: auto;
        }
        
        .input-actions {
            display: flex;
            align-items: center;
        }
        
        .action-button {
            background: none;
            border: none;
            padding: 0.5rem;
            cursor: pointer;
            color: #9ca3af;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.2s;
        }
        
        .action-button:hover {
            color: var(--primary-color);
        }
        
        .send-button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            width: 32px;
            height: 32px;
            border-radius: 0.25rem;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            margin-right: 0.5rem;
            transition: background-color 0.2s;
        }
        
        .send-button:hover {
            background-color: #0d8c6d;
        }
        
        .send-button:disabled {
            background-color: #e5e7eb;
            cursor: not-allowed;
        }
        
        .file-input {
            display: none;
        }
        
        .file-preview {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            background-color: var(--hover-color);
            border-radius: var(--radius);
            margin-bottom: 0.5rem;
            font-size: 0.75rem;
        }
        
        .file-name {
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .remove-file {
            color: #9ca3af;
            cursor: pointer;
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
            overflow-x: auto;
            display: block;
        }
        
        table th {
            background-color: var(--hover-color);
            text-align: left;
            padding: 0.5rem;
            font-weight: 500;
        }
        
        table td {
            padding: 0.5rem;
            border-top: 1px solid var(--border-color);
        }
        
        pre {
            background-color: var(--hover-color);
            padding: 0.75rem;
            border-radius: var(--radius);
            overflow-x: auto;
            font-size: 0.875rem;
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            margin: 0.5rem 0;
        }
        
        .processing-steps {
            background-color: var(--secondary-color);
            border-radius: var(--radius);
            padding: 0.75rem;
            margin: 0.5rem 0;
            font-size: 0.875rem;
        }
        
        .processing-step {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0.25rem 0;
        }
        
        .step-icon {
            color: var(--primary-color);
        }
        
        .completion-message {
            background-color: rgba(16, 163, 127, 0.1);
            border-left: 3px solid var(--primary-color);
            padding: 0.75rem;
            border-radius: 0 var(--radius) var(--radius) 0;
            margin: 0.5rem 0;
        }
        
        @media (max-width: 768px) {
            .chat-container {
                max-width: 100%;
                padding: 0;
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
        
        <div id="filePreview" style="padding: 0 1rem; display: none;"></div>
        
        <div class="input-area">
            <div class="input-container">
                <input type="text" id="query" class="input-field" placeholder="Ask a question or upload a file..." />
                <div class="input-actions">
                    <label for="file" class="action-button">
                        <i class="fas fa-paperclip"></i>
                        <input type="file" id="file" class="file-input" accept=".csv,.json,.xml,.yaml,.yml,.xlsx,.xls">
                    </label>
                    <button id="sendButton" class="send-button" disabled>
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Hidden elements for compatibility -->
    <div id="uploadStatus" style="display: none;"></div>
    <button id="clearCacheBtn" style="display: none;"></button>
    <button id="uploadBtn" style="display: none;"></button>
    <button id="queryBtn" style="display: none;"></button>
    <div id="results" style="display: none;"></div>
    
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
        
        // Handle file selection
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const fileName = file.name;
                const fileExt = fileName.split('.').pop().toLowerCase();
                
                // Determine appropriate icon
                let fileIcon = 'fa-file-alt';
                if (fileExt === 'csv') fileIcon = 'fa-file-csv';
                else if (fileExt === 'json') fileIcon = 'fa-file-code';
                else if (['xlsx', 'xls'].includes(fileExt)) fileIcon = 'fa-file-excel';
                else if (fileExt === 'xml') fileIcon = 'fa-file-code';
                else if (['yaml', 'yml'].includes(fileExt)) fileIcon = 'fa-file-code';
                
                // Show file preview
                filePreview.style.display = 'block';
                filePreview.innerHTML = `
                    <div class="file-preview">
                        <i class="fas ${fileIcon}"></i>
                        <span class="file-name">${fileName}</span>
                        <span class="remove-file" id="removeFile">
                            <i class="fas fa-times"></i>
                        </span>
                    </div>
                `;
                
                // Add user message
                addUserMessage(`I'm uploading <strong>${fileName}</strong> for analysis.`);
                
                // Add initial bot response
                addTypingIndicator();
                
                // Enable send button
                sendButton.disabled = false;
                
                // Add event listener for remove button
                document.getElementById('removeFile').addEventListener('click', () => {
                    filePreview.style.display = 'none';
                    filePreview.innerHTML = '';
                    fileInput.value = '';
                    if (!queryInput.value.trim()) {
                        sendButton.disabled = true;
                    }
                });
                
                // Automatically trigger upload
                uploadFile(file);
            }
        });
        
        // Handle query input
        queryInput.addEventListener('input', () => {
            sendButton.disabled = !queryInput.value.trim() && !fileInput.files.length;
        });
        
        // Handle send button click
        sendButton.addEventListener('click', () => {
            const query = queryInput.value.trim();
            if (query) {
                // Add user message
                addUserMessage(query);
                
                // Clear input
                queryInput.value = '';
                sendButton.disabled = true;
                
                // Process query
                if (dataDictPath && dbPath) {
                    processQuery(query);
                } else {
                    addBotMessage('Please upload a data file first before asking questions.');
                }
            } else if (fileInput.files.length) {
                // If no query but file is selected, just upload the file
                uploadFile(fileInput.files[0]);
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
                const uploadResponse = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!uploadResponse.ok) {
                    const errorText = await uploadResponse.text();
                    throw new Error(`Server error: ${uploadResponse.status} ${errorText}`);
                }
                
                // Parse response
                const responseText = await uploadResponse.text();
                const cleanedText = responseText.replace(/: ?NaN/g, ': null');
                const uploadData = JSON.parse(cleanedText);
                
                if (!uploadData.success) {
                    throw new Error(uploadData.error || 'Error uploading file');
                }
                
                // Remove typing indicator
                removeTypingIndicator();
                
                // Display file analysis
                const analysis = uploadData.analysis;
                const fileType = analysis.file_type || 'Unknown';
                const fileDescription = analysis.description || 'No description available';
                const fileRecommendation = analysis.recommendation || 'No recommendation available';
                
                // Add analysis message
                const analysisMessage = `
                    <p>I've analyzed your file and detected it's a <strong>${fileType}</strong> file.</p>
                    <p style="margin-top: 0.5rem;">${fileDescription}</p>
                    <p style="margin-top: 0.5rem;"><strong>Recommendation:</strong> ${fileRecommendation}</p>
                `;
                
                addBotMessage(analysisMessage);
                
                // Add transition message
                addBotMessage('<div class="processing-steps"><p>Now setting up your database for querying...</p></div>');
                
                // Analyze data
                const analyzeResponse = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        file_path: uploadData.file_path,
                        analysis: uploadData.analysis
                    })
                });
                
                if (!analyzeResponse.ok) {
                    const errorText = await analyzeResponse.text();
                    throw new Error(`Server error: ${analyzeResponse.status} ${errorText}`);
                }
                
                // Parse analyze response
                const analyzeText = await analyzeResponse.text();
                const cleanedAnalyzeText = analyzeText.replace(/: ?NaN/g, ': null');
                const analyzeData = JSON.parse(cleanedAnalyzeText);
                
                if (!analyzeData.success) {
                    throw new Error(analyzeData.error || 'Error analyzing data');
                }
                
                // Set global paths
                dataDictPath = analyzeData.data_dict_path;
                dbPath = analyzeData.db_path;
                
                // Show processing steps
                const processingSteps = `
                    <div class="processing-steps">
                        <div class="processing-step">
                            <span class="step-icon"><i class="fas fa-check-circle"></i></span>
                            <span>File uploaded successfully</span>
                        </div>
                        <div class="processing-step">
                            <span class="step-icon"><i class="fas fa-check-circle"></i></span>
                            <span>Data parsed successfully</span>
                        </div>
                        <div class="processing-step">
                            <span class="step-icon"><i class="fas fa-check-circle"></i></span>
                            <span>Database created</span>
                        </div>
                        <div class="processing-step">
                            <span class="step-icon"><i class="fas fa-check-circle"></i></span>
                            <span>Schema analyzed</span>
                        </div>
                        <div class="processing-step">
                            <span class="step-icon"><i class="fas fa-check-circle"></i></span>
                            <span>Database ready</span>
                        </div>
                    </div>
                `;
                
                // Show completion message
                const completionMessage = `
                    <div class="completion-message">
                        <p><strong>Analysis Complete</strong></p>
                        <p>Your data is ready for querying. You can now ask questions about your dataset.</p>
                    </div>
                `;
                
                addBotMessage(processingSteps + completionMessage);
                
                // Enable send button for queries
                sendButton.disabled = !queryInput.value.trim();
                
            } catch (error) {
                console.error('Error uploading file:', error);
                removeTypingIndicator();
                addBotMessage(`<p style="color: #ef4444;"><i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${error.message}</p>`);
            }
        }
        
        // Function to process query
        async function processQuery(query) {
            try {
                // Show typing indicator
                addTypingIndicator();
                
                // Send query to server
                const response = await fetch('/api/process_query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query,
                        data_dict_path: dataDictPath,
                        db_path: dbPath
                    })
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Server error: ${response.status} ${errorText}`);
                }
                
                const data = await response.json();
                
                // Remove typing indicator
                removeTypingIndicator();
                
                if (!data.success) {
                    throw new Error(data.error || 'Failed to process query');
                }
                
                const result = data.result;
                
                // Build response message
                let responseHTML = '<div>';
                
                // Add SQL query
                responseHTML += `
                    <div>
                        <p><strong>SQL Query:</strong></p>
                        <pre>${result.sql_query}</pre>
                    </div>
                `;
                
                // Add reasoning if available
                if (result.reasoning) {
                    responseHTML += `
                        <div>
                            <p><strong>Reasoning:</strong></p>
                            <p>${result.reasoning}</p>
                        </div>
                    `;
                }
                
                // Add results
                if (result.results && result.results.length > 0) {
                    // Get columns from first result
                    const columns = Object.keys(result.results[0]);
                    
                    responseHTML += `
                        <div>
                            <p><strong>Results:</strong></p>
                            <table>
                                <thead>
                                    <tr>
                                        ${columns.map(col => `<th>${col}</th>`).join('')}
                                    </tr>
                                </thead>
                                <tbody>
                                    ${result.results.map(row => `
                                        <tr>
                                            ${columns.map(col => `<td>${row[col] !== null ? row[col] : 'NULL'}</td>`).join('')}
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                } else {
                    responseHTML += `
                        <div>
                            <p><strong>Results:</strong></p>
                            <p>No results found for your query.</p>
                        </div>
                    `;
                }
                
                responseHTML += '</div>';
                
                // Add bot response
                addBotMessage(responseHTML);
                
                // Enable send button
                sendButton.disabled = !queryInput.value.trim();
                
            } catch (error) {
                console.error('Error processing query:', error);
                removeTypingIndicator();
                addBotMessage(`<p style="color: #ef4444;"><i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${error.message}</p>`);
                sendButton.disabled = !queryInput.value.trim();
            }
        }
    </script>
</body>
</html>
    """

if __name__ == '__main__':
    app.run(debug=True, port=5000)
