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
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NL2SQL Tool</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {
                --primary: #4F46E5;
                --primary-hover: #4338CA;
                --secondary: #10B981;
                --dark: #1F2937;
                --light: #F9FAFB;
                --gray: #9CA3AF;
                --border: #E5E7EB;
                --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                --radius: 8px;
            }
            
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                background-color: #F3F4F6;
                color: var(--dark);
                line-height: 1.6;
                padding: 0;
                margin: 0;
            }
            
            .app-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .app-header {
                background-color: white;
                box-shadow: var(--shadow);
                padding: 1.5rem 2rem;
                margin-bottom: 2rem;
                border-radius: var(--radius);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .app-title {
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }
            
            .app-title h1 {
                color: var(--dark);
                font-size: 1.5rem;
                font-weight: 700;
                margin: 0;
            }
            
            .app-title .logo {
                background-color: var(--primary);
                color: white;
                width: 40px;
                height: 40px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 1.25rem;
            }
            
            .app-description {
                color: var(--gray);
                max-width: 600px;
                margin-bottom: 2rem;
            }
            
            .container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
            }
            
            .card {
                background-color: white;
                border-radius: var(--radius);
                box-shadow: var(--shadow);
                padding: 1.5rem;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            }
            
            .card h2 {
                font-size: 1.25rem;
                font-weight: 600;
                margin-bottom: 1rem;
                color: var(--dark);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .card h2 .icon {
                background-color: var(--primary);
                color: white;
                width: 28px;
                height: 28px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.875rem;
            }
            
            .form-group {
                margin-bottom: 1.25rem;
            }
            
            label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 500;
                font-size: 0.875rem;
                color: var(--dark);
            }
            
            .file-input-wrapper {
                position: relative;
                width: 100%;
                height: 100px;
                border: 2px dashed var(--border);
                border-radius: var(--radius);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: border-color 0.2s;
                overflow: hidden;
            }
            
            .file-input-wrapper:hover {
                border-color: var(--primary);
            }
            
            .file-input-wrapper input[type=file] {
                position: absolute;
                width: 100%;
                height: 100%;
                opacity: 0;
                cursor: pointer;
            }
            
            .file-input-content {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 0.5rem;
                color: var(--gray);
                font-size: 0.875rem;
            }
            
            .file-input-icon {
                font-size: 1.5rem;
                color: var(--primary);
            }
            
            textarea {
                width: 100%;
                padding: 0.75rem 1rem;
                border: 1px solid var(--border);
                border-radius: var(--radius);
                font-size: 0.875rem;
                font-family: inherit;
                resize: vertical;
                min-height: 120px;
                transition: border-color 0.2s;
                outline: none;
            }
            
            textarea:focus {
                border-color: var(--primary);
                box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
            }
            
            button {
                background-color: var(--primary);
                color: white;
                border: none;
                padding: 0.75rem 1.25rem;
                border-radius: var(--radius);
                font-weight: 500;
                cursor: pointer;
                transition: background-color 0.2s;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.875rem;
            }
            
            button:hover {
                background-color: var(--primary-hover);
            }
            
            #fileInfo, #results {
                margin-top: 1.25rem;
                background-color: var(--light);
                border-radius: var(--radius);
                padding: 1.25rem;
                font-size: 0.875rem;
            }
            
            #results {
                display: none;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
                gap: 0.75rem;
                margin: 1rem 0;
            }
            
            .stat-item {
                background-color: white;
                border-radius: var(--radius);
                padding: 0.75rem;
                text-align: center;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            }
            
            .stat-value {
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--primary);
            }
            
            .stat-label {
                font-size: 0.75rem;
                color: var(--gray);
                margin-top: 0.25rem;
            }
            
            h3 {
                font-size: 1rem;
                font-weight: 600;
                margin-bottom: 0.75rem;
                color: var(--dark);
            }
            
            h4 {
                font-size: 0.875rem;
                font-weight: 600;
                margin: 1rem 0 0.5rem;
                color: var(--dark);
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 1rem 0;
                font-size: 0.875rem;
            }
            
            table th {
                background-color: var(--light);
                text-align: left;
                padding: 0.75rem;
                font-weight: 500;
                color: var(--dark);
                border-bottom: 1px solid var(--border);
            }
            
            table td {
                padding: 0.75rem;
                border-bottom: 1px solid var(--border);
            }
            
            table tr:last-child td {
                border-bottom: none;
            }
            
            .success-message {
                color: var(--secondary);
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.75rem;
            }
            
            .error-message {
                color: #EF4444;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.75rem;
            }
            
            pre {
                background-color: #1F2937;
                color: #F9FAFB;
                padding: 1rem;
                border-radius: var(--radius);
                overflow-x: auto;
                font-size: 0.875rem;
                font-family: 'Fira Code', 'Courier New', Courier, monospace;
            }
            
            .loading {
                display: inline-block;
                width: 1rem;
                height: 1rem;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                border-top-color: white;
                animation: spin 1s ease-in-out infinite;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            .typing-animation::after {
                content: '|';
                animation: blink 1s infinite;
                margin-left: 2px;
            }
            
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0; }
            }
            
            @media (max-width: 768px) {
                .app-container {
                    padding: 1rem;
                }
                
                .container {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <div class="app-header">
                <div class="app-title">
                    <div class="logo">NL</div>
                    <h1>NL2SQL Tool</h1>
                </div>
            </div>
            
            <p class="app-description">An agentic AI application that converts natural language queries to SQL and executes them on your data.</p>
            
            <div class="container">
                <div class="card">
                    <h2><span class="icon"><i class="fas fa-upload"></i></span> Upload Data</h2>
                    <div class="form-group">
                        <label for="file">Select a data file to analyze (CSV, JSON, XML, YAML, Excel)</label>
                        <div class="file-input-wrapper">
                            <input type="file" id="file" accept=".csv,.json,.xml,.yaml,.yml,.xlsx,.xls">
                            <div class="file-input-content">
                                <div class="file-input-icon"><i class="fas fa-file-alt"></i></div>
                                <span>Drop your data file here or click to browse</span>
                            </div>
                        </div>
                    </div>
                    <div class="button-group" style="display: flex; gap: 10px;">
                        <button id="uploadBtn">
                            <span>Upload & Analyze</span>
                        </button>
                        <button id="clearCacheBtn" style="background-color: #64748B;">
                            <span><i class="fas fa-trash"></i> Clear Cache</span>
                        </button>
                    </div>
                    <div id="uploadStatus" style="display: none; margin-top: 1rem;"></div>
                    <div id="fileInfo" style="display: none;"></div>
                    <div id="analysisSection" style="display: none; margin-top: 1rem;">
                        <h3><i class="fas fa-brain" style="color: var(--primary); margin-right: 0.5rem;"></i>AI Analysis</h3>
                        <div class="chat-container" style="background-color: #f9fafb; border-radius: 12px; padding: 1.25rem; margin-top: 0.5rem; font-size: 0.9rem; line-height: 1.5; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                            <div class="chat-message" style="display: flex; margin-bottom: 0.5rem;">
                                <div style="background-color: var(--primary); color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; margin-right: 0.75rem; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                    <i class="fas fa-robot" style="font-size: 0.85rem;"></i>
                                </div>
                                <div id="aiAnalysisContent" style="flex-grow: 1;">
                                    <div class="ai-name" style="font-weight: 600; color: var(--primary); margin-bottom: 0.5rem; font-size: 0.85rem;">GPT-4.1 Nano</div>
                                    <div id="fileTypeMessage" class="" style="background-color: rgba(255,255,255,0.7); padding: 0.75rem; border-radius: 8px; border-left: 3px solid var(--primary);"></div>
                                    <div id="fileDescriptionMessage" style="margin-top: 0.75rem; background-color: rgba(255,255,255,0.7); padding: 0.75rem; border-radius: 8px; border-left: 3px solid var(--secondary);"></div>
                                    <div id="fileRecommendationMessage" style="margin-top: 0.75rem; background-color: rgba(255,255,255,0.7); padding: 0.75rem; border-radius: 8px; border-left: 3px solid #10B981;"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card" id="querySection">
                    <h2><span class="icon"><i class="fas fa-search"></i></span> Query Data</h2>
                    <div class="form-group">
                        <label for="query">Ask a question about your data in natural language</label>
                        <textarea id="query" placeholder="Example: Show me the top 5 customers by revenue"></textarea>
                    </div>
                    <button id="queryBtn">
                        <span>Process Query</span>
                    </button>
                    <div id="results"></div>
                </div>
            </div>
        </div>
        
        <script>
            let dataDictPath = null;
            let dbPath = null;
            
            // Handle Clear Cache button click
            document.getElementById('clearCacheBtn').addEventListener('click', async () => {
                // Show loading state
                const clearCacheBtn = document.getElementById('clearCacheBtn');
                const originalBtnText = clearCacheBtn.innerHTML;
                clearCacheBtn.innerHTML = '<span class="loading"></span><span>Clearing...</span>';
                clearCacheBtn.disabled = true;
                
                try {
                    // Call the clear cache API endpoint
                    const response = await fetch('/api/clear_cache', {
                        method: 'POST'
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        // Show success message
                        const fileInfo = document.getElementById('fileInfo');
                        fileInfo.innerHTML = `
                            <div class="success-message" style="margin-top: 1rem;">
                                <i class="fas fa-check-circle"></i>
                                <span><strong>Success!</strong> ${result.message}</span>
                            </div>
                        `;
                        fileInfo.style.display = 'block';
                        
                        // Reset file input
                        document.getElementById('file').value = '';
                        const fileContent = document.querySelector('.file-input-content');
                        fileContent.innerHTML = `
                            <div class="file-input-icon"><i class="fas fa-file-alt"></i></div>
                            <span>Drop your data file here or click to browse</span>
                        `;
                        
                        // Reset global variables
                        dataDictPath = null;
                        dbPath = null;
                        
                        // Clear results
                        document.getElementById('results').innerHTML = '';
                        document.getElementById('query').value = '';
                    } else {
                        throw new Error(result.error || 'Failed to clear cache');
                    }
                } catch (error) {
                    console.error('Error clearing cache:', error);
                    const fileInfo = document.getElementById('fileInfo');
                    fileInfo.innerHTML = `
                        <div class="error-message">
                            <i class="fas fa-exclamation-circle"></i>
                            <span><strong>Error:</strong> ${error.message}</span>
                        </div>
                    `;
                    fileInfo.style.display = 'block';
                } finally {
                    // Reset button state
                    clearCacheBtn.innerHTML = originalBtnText;
                    clearCacheBtn.disabled = false;
                }
            });
            
            // Update file input display when file is selected
            document.getElementById('file').addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    const fileName = file.name;
                    const fileExt = fileName.split('.').pop().toLowerCase();
                    
                    // Determine the appropriate icon based on file extension
                    let fileIcon = 'fa-file-alt';
                    if (fileExt === 'csv') {
                        fileIcon = 'fa-file-csv';
                    } else if (fileExt === 'json') {
                        fileIcon = 'fa-file-code';
                    } else if (['xlsx', 'xls'].includes(fileExt)) {
                        fileIcon = 'fa-file-excel';
                    } else if (fileExt === 'xml') {
                        fileIcon = 'fa-file-code';
                    } else if (['yaml', 'yml'].includes(fileExt)) {
                        fileIcon = 'fa-file-code';
                    }
                    
                    const fileContent = document.querySelector('.file-input-content');
                    fileContent.innerHTML = `
                        <div class="file-input-icon" style="color: var(--secondary);"><i class="fas ${fileIcon}"></i></div>
                        <span>${fileName}</span>
                    `;
                }
            });
            
            document.getElementById('uploadBtn').addEventListener('click', async () => {
                const fileInput = document.getElementById('file');
                if (!fileInput.files.length) {
                    const fileInputWrapper = document.querySelector('.file-input-wrapper');
                    fileInputWrapper.style.borderColor = '#EF4444';
                    setTimeout(() => {
                        fileInputWrapper.style.borderColor = '';
                    }, 2000);
                    return;
                }
                
                const file = fileInput.files[0];
                if (!file) return;
                
                // Show loading state
                const uploadBtn = document.getElementById('uploadBtn');
                const originalBtnText = uploadBtn.innerHTML;
                uploadBtn.innerHTML = '<span class="loading"></span><span>Processing...</span>';
                uploadBtn.disabled = true;
                
                // Show loading message
                const fileInfo = document.getElementById('fileInfo');
                fileInfo.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> Uploading and processing file... Please wait.</p>';
                fileInfo.style.display = 'block';
                
                // Hide other sections
                document.getElementById('analysisSection').style.display = 'none';
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    // Upload file
                    console.log('Uploading file...');
                    let uploadData;
                    
                    try {
                        const uploadResponse = await fetch('/api/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        // Check if response is OK
                        if (!uploadResponse.ok) {
                            const errorText = await uploadResponse.text();
                            throw new Error(`Server error: ${uploadResponse.status} ${errorText}`);
                        }
                        
                        // Get response as text
                        const responseText = await uploadResponse.text();
                        console.log('Response text:', responseText);
                        
                        // Handle NaN values by replacing them with null
                        const cleanedText = responseText.replace(/: ?NaN/g, ': null');
                        
                        // Parse the cleaned JSON
                        uploadData = JSON.parse(cleanedText);
                        console.log('Upload data:', uploadData);
                    } catch (parseError) {
                        console.error('Error parsing upload response:', parseError);
                        throw new Error(`Failed to parse server response: ${parseError.message}`);
                    }
                    
                    if (!uploadData.success) {
                        throw new Error(uploadData.error || 'Error uploading file');
                    }
                    
                    // Display file info
                    fileInfo.innerHTML = `
                        <h3>File Information</h3>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-value">${uploadData.stats.rows}</div>
                                <div class="stat-label">Rows</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${uploadData.stats.columns}</div>
                                <div class="stat-label">Columns</div>
                            </div>
                        </div>
                        <h4>Data Preview</h4>
                        <div class="data-preview-container" style="max-height: 200px; overflow-y: auto; overflow-x: auto; border: 1px solid #E5E7EB; border-radius: 8px;">
                            <table id="previewTable" class="data-table" style="font-size: 0.8rem;"></table>
                        </div>
                    `;
                    
                    // Show data preview
                    const previewTable = document.getElementById('previewTable');
                    
                    // Create header row
                    if (uploadData.stats.preview.length > 0) {
                        const headerRow = document.createElement('tr');
                        Object.keys(uploadData.stats.preview[0]).forEach(key => {
                            const th = document.createElement('th');
                            th.textContent = key;
                            headerRow.appendChild(th);
                        });
                        previewTable.appendChild(headerRow);
                        
                        // Create data rows
                        uploadData.stats.preview.forEach(row => {
                            const tr = document.createElement('tr');
                            Object.values(row).forEach(value => {
                                const td = document.createElement('td');
                                td.textContent = value !== null ? value : 'null';
                                tr.appendChild(td);
                            });
                            previewTable.appendChild(tr);
                        });
                    }
                    
                    // Display LLM analysis if available with streaming effect
                    if (uploadData.analysis) {
                        const analysisSection = document.getElementById('analysisSection');
                        analysisSection.style.display = 'block';
                        
                        // Get analysis content
                        const fileType = uploadData.analysis.file_type || 'Unknown';
                        const fileDescription = uploadData.analysis.description || 'No description available';
                        const fileRecommendation = uploadData.analysis.recommendation || 'No recommendation available';
                        
                        // Get message containers
                        const fileTypeMessage = document.getElementById('fileTypeMessage');
                        const fileDescriptionMessage = document.getElementById('fileDescriptionMessage');
                        const fileRecommendationMessage = document.getElementById('fileRecommendationMessage');
                        
                        // Clear previous content
                        fileTypeMessage.textContent = '';
                        fileTypeMessage.classList.add('typing-animation');
                        fileDescriptionMessage.textContent = '';
                        fileRecommendationMessage.textContent = '';
                        
                        // We'll handle this in the chat interface instead
                        
                        // Simulate typing for file type
                        const typeText = `I've analyzed your file and detected it's a ${fileType} file.`;
                        let typeIndex = 0;
                        
                        function typeFileType() {
                            if (typeIndex < typeText.length) {
                                fileTypeMessage.textContent += typeText.charAt(typeIndex);
                                typeIndex++;
                                setTimeout(typeFileType, 20 + Math.random() * 30);
                            } else {
                                fileTypeMessage.classList.remove('typing-animation');
                                setTimeout(typeFileDescription, 500);
                            }
                        }
                        
                        // Simulate typing for description
                        function typeFileDescription() {
                            fileDescriptionMessage.classList.add('typing-animation');
                            let descIndex = 0;
                            
                            function typeDesc() {
                                if (descIndex < fileDescription.length) {
                                    fileDescriptionMessage.textContent += fileDescription.charAt(descIndex);
                                    descIndex++;
                                    setTimeout(typeDesc, 5 + Math.random() * 15);
                                } else {
                                    fileDescriptionMessage.classList.remove('typing-animation');
                                    setTimeout(typeFileRecommendation, 500);
                                }
                            }
                            
                            typeDesc();
                        }
                        
                        // Simulate typing for recommendation
                        function typeFileRecommendation() {
                            fileRecommendationMessage.classList.add('typing-animation');
                            const recText = `Recommendation: ${fileRecommendation}`;
                            let recIndex = 0;
                            
                            function typeRec() {
                                if (recIndex < recText.length) {
                                    fileRecommendationMessage.textContent += recText.charAt(recIndex);
                                    recIndex++;
                                    setTimeout(typeRec, 10 + Math.random() * 20);
                                } else {
                                    fileRecommendationMessage.classList.remove('typing-animation');
                                    
                                    // Add a transition message to explain what's happening next
                                    setTimeout(() => {
                                        // Create a transition message element
                                        const transitionMessage = document.createElement('div');
                                        transitionMessage.id = 'transitionMessage';
                                        transitionMessage.style.marginTop = '0.75rem';
                                        transitionMessage.style.backgroundColor = 'rgba(255,255,255,0.7)';
                                        transitionMessage.style.padding = '0.75rem';
                                        transitionMessage.style.borderRadius = '8px';
                                        transitionMessage.style.borderLeft = '3px solid #6366F1';
                                        transitionMessage.style.color = '#4B5563';
                                        transitionMessage.style.fontSize = '0.85rem';
                                        transitionMessage.innerHTML = '<i class="fas fa-database"></i> Now setting up your database for querying...';
                                        
                                        // Add it before the processing steps
                                        const aiAnalysisContent = document.getElementById('aiAnalysisContent');
                                        const processingStepsMessage = document.getElementById('processingStepsMessage');
                                        aiAnalysisContent.insertBefore(transitionMessage, processingStepsMessage);
                                    }, 500);
                                }
                            }
                            
                            typeRec();
                        }
                        
                        // Start the typing animation
                        setTimeout(typeFileType, 500);
                    }
                    
                    // Show the AI Analysis section early with a loading message
                    const analysisSection = document.getElementById('analysisSection');
                    analysisSection.style.display = 'block';
                    
                    const fileTypeMessage = document.getElementById('fileTypeMessage');
                    fileTypeMessage.innerHTML = 'Analyzing your data... <i class="fas fa-spinner fa-spin"></i>';
                    
                    // Add additional message containers for processing steps
                    const aiAnalysisContent = document.getElementById('aiAnalysisContent');
                    const processingStepsMessage = document.createElement('div');
                    processingStepsMessage.id = 'processingStepsMessage';
                    processingStepsMessage.style.marginTop = '1rem';
                    processingStepsMessage.style.padding = '0.75rem';
                    processingStepsMessage.style.backgroundColor = 'rgba(243, 244, 246, 0.7)';
                    processingStepsMessage.style.borderRadius = '8px';
                    processingStepsMessage.style.color = '#4B5563';
                    processingStepsMessage.style.fontSize = '0.8rem';
                    processingStepsMessage.style.borderLeft = '3px solid #6366F1';
                    processingStepsMessage.innerHTML = '<div style="font-weight: 600; margin-bottom: 0.5rem; color: #4F46E5;"><i class="fas fa-cog fa-spin"></i> Processing Pipeline</div><div>• <i class="fas fa-cog fa-spin"></i> Processing file...</div>';
                    aiAnalysisContent.appendChild(processingStepsMessage);
                    
                    // Add container for completion message
                    const completionMessage = document.createElement('div');
                    completionMessage.id = 'completionMessage';
                    completionMessage.style.marginTop = '1rem';
                    completionMessage.style.display = 'none';
                    aiAnalysisContent.appendChild(completionMessage);
                    
                    // Analyze data
                    console.log('Analyzing data...');
                    let analyzeData;
                    
                    try {
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
                        
                        // Check if response is OK
                        if (!analyzeResponse.ok) {
                            const errorText = await analyzeResponse.text();
                            throw new Error(`Server error: ${analyzeResponse.status} ${errorText}`);
                        }
                        
                        // Get response as text
                        const responseText = await analyzeResponse.text();
                        console.log('Analyze response text:', responseText);
                        
                        // Update processing steps
                        const processingStepsMessage = document.getElementById('processingStepsMessage');
                        processingStepsMessage.innerHTML += '<br><i class="fas fa-check"></i> File uploaded successfully';
                        
                        // Handle NaN values by replacing them with null
                        const cleanedText = responseText.replace(/: ?NaN/g, ': null');
                        
                        // Parse the cleaned JSON
                        analyzeData = JSON.parse(cleanedText);
                        console.log('Analyze data:', analyzeData);
                        
                        // Update processing steps - but don't show all steps immediately
                        setTimeout(() => {
                            // First, make sure we're starting with the correct base content
                            processingStepsMessage.innerHTML = '<div style="font-weight: 600; margin-bottom: 0.5rem; color: #4F46E5;"><i class="fas fa-cog fa-spin"></i> Processing Pipeline</div><div>• <i class="fas fa-check-circle" style="color: #10B981;"></i> File uploaded successfully</div><div>• <i class="fas fa-cog fa-spin"></i> Parsing data...</div>';
                        }, 500);
                        
                        setTimeout(() => {
                            // Update the parsing data step
                            processingStepsMessage.innerHTML = processingStepsMessage.innerHTML.replace('<i class="fas fa-cog fa-spin"></i> Parsing data...', '<i class="fas fa-check-circle" style="color: #10B981;"></i> Data parsed successfully');
                            processingStepsMessage.innerHTML += '<div>• <i class="fas fa-cog fa-spin"></i> Creating database...</div>';
                        }, 1000);
                        
                        setTimeout(() => {
                            // Update the creating database step
                            processingStepsMessage.innerHTML = processingStepsMessage.innerHTML.replace('<i class="fas fa-cog fa-spin"></i> Creating database...', '<i class="fas fa-check-circle" style="color: #10B981;"></i> Database created');
                            processingStepsMessage.innerHTML += '<div>• <i class="fas fa-cog fa-spin"></i> Analyzing schema...</div>';
                        }, 1500);
                        
                        setTimeout(() => {
                            // Update the analyzing schema step
                            processingStepsMessage.innerHTML = processingStepsMessage.innerHTML.replace('<i class="fas fa-cog fa-spin"></i> Analyzing schema...', '<i class="fas fa-check-circle" style="color: #10B981;"></i> Schema analyzed');
                            
                            // Add final processing step
                            setTimeout(() => {
                                // Add finalizing database step
                                processingStepsMessage.innerHTML += '<div>• <i class="fas fa-cog fa-spin"></i> Finalizing database...</div>';
                                
                                // Hide transition message when we're almost done
                                const transitionMessage = document.getElementById('transitionMessage');
                                if (transitionMessage) {
                                    transitionMessage.style.opacity = '0.7';
                                }
                                
                                setTimeout(() => {
                                    // Update the finalizing database step
                                    processingStepsMessage.innerHTML = processingStepsMessage.innerHTML.replace('<i class="fas fa-cog fa-spin"></i> Finalizing database...', '<i class="fas fa-check-circle" style="color: #10B981;"></i> Database ready');
                                    
                                    // Now show the completion message after all steps are truly done
                                    setTimeout(() => {
                                        // Remove the transition message
                                        if (transitionMessage) {
                                            transitionMessage.remove();
                                        }
                                        
                                        // Show completion message
                                        const completionMessage = document.getElementById('completionMessage');
                                        completionMessage.style.display = 'block';
                                        completionMessage.innerHTML = `
                                            <div style="background-color: rgba(16, 185, 129, 0.1); border-left: 3px solid #10B981; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                                    <div style="background-color: #10B981; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                                                        <i class="fas fa-check"></i>
                                                    </div>
                                                    <div>
                                                        <div style="font-weight: 600; color: #10B981; font-size: 0.95rem;">Analysis Complete</div>
                                                        <div style="color: #4B5563; margin-top: 0.25rem;">Your data is ready for querying. You can now ask questions about your dataset.</div>
                                                    </div>
                                                </div>
                                            </div>
                                        `;
                                        
                                        // Make processing steps less prominent
                                        processingStepsMessage.style.opacity = '0.8';
                                    }, 800);
                                }, 800);
                            }, 800);
                        }, 2000);
                    } catch (parseError) {
                        console.error('Error parsing analyze response:', parseError);
                        throw new Error(`Failed to parse server response: ${parseError.message}`);
                    }
                    
                    if (!analyzeData.success) {
                        throw new Error(analyzeData.error || 'Error analyzing data');
                    }
                    
                    dataDictPath = analyzeData.data_dict_path;
                    dbPath = analyzeData.db_path;
                    
                    // Update file info to show analysis is complete
                    fileInfo.innerHTML = `
                        <h3>File Information</h3>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-value">${uploadData.stats.rows}</div>
                                <div class="stat-label">Rows</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${uploadData.stats.columns}</div>
                                <div class="stat-label">Columns</div>
                            </div>
                        </div>
                        <h4>Data Preview</h4>
                        <div class="data-preview-container" style="max-height: 200px; overflow-y: auto; overflow-x: auto; border: 1px solid #E5E7EB; border-radius: 8px;">
                            <table id="previewTable" class="data-table" style="font-size: 0.8rem;"></table>
                        </div>
                    `;
                    
                    // Reset button state
                    uploadBtn.innerHTML = originalBtnText;
                    uploadBtn.disabled = false;
                    
                    // Show query section
                    document.getElementById('querySection').style.display = 'block';
                    
                } catch (error) {
                    console.error('Error:', error);
                    fileInfo.innerHTML = `
                        <div class="error-message">
                            <span style="font-size: 1.25rem;">⚠️</span>
                            <span><strong>Error:</strong> ${error.message}</span>
                        </div>
                    `;
                    
                    // Reset button state
                    uploadBtn.innerHTML = originalBtnText;
                    uploadBtn.disabled = false;
                }
            });
            
            document.getElementById('queryBtn').addEventListener('click', async () => {
                const query = document.getElementById('query').value.trim();
                if (!query) {
                    const textarea = document.getElementById('query');
                    textarea.style.borderColor = '#EF4444';
                    setTimeout(() => {
                        textarea.style.borderColor = '';
                    }, 2000);
                    return;
                }
                
                if (!dataDictPath) {
                    alert('Please upload and analyze a data file first');
                    return;
                }
                
                // Show loading state
                const queryBtn = document.getElementById('queryBtn');
                const originalBtnText = queryBtn.innerHTML;
                queryBtn.innerHTML = '<span class="loading"></span><span>Processing...</span>';
                queryBtn.disabled = true;
                
                // Show loading message
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = `
                    <p>Processing your query... <span class="loading" style="border-color: rgba(79, 70, 229, 0.3); border-top-color: var(--primary);"></span></p>
                    <p><em>"${query}"</em></p>
                `;
                resultsDiv.style.display = 'block';
                
                try {
                    console.log('Processing query:', query);
                    let data;
                    
                    try {
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
                        
                        // Check if response is OK
                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`Server error: ${response.status} ${errorText}`);
                        }
                        
                        // Get response as text
                        const responseText = await response.text();
                        console.log('Query response text:', responseText);
                        
                        // Handle NaN values by replacing them with null
                        const cleanedText = responseText.replace(/: ?NaN/g, ': null');
                        
                        // Parse the cleaned JSON
                        data = JSON.parse(cleanedText);
                        console.log('Query data:', data);
                    } catch (parseError) {
                        console.error('Error parsing query response:', parseError);
                        throw new Error(`Failed to parse server response: ${parseError.message}`);
                    }
                    
                    if (!data.success) {
                        throw new Error(data.error || 'Error processing query');
                    }
                    
                    const result = data.result;
                    
                    // Format results as a table if it's an array of objects
                    let resultsHtml = '';
                    if (Array.isArray(result.results) && result.results.length > 0 && typeof result.results[0] === 'object') {
                        // Get all unique keys from all objects
                        const keys = Array.from(new Set(
                            result.results.flatMap(obj => Object.keys(obj))
                        ));
                        
                        resultsHtml = `
                            <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
                                <thead>
                                    <tr>
                                        ${keys.map(key => `<th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">${key}</th>`).join('')}
                                    </tr>
                                </thead>
                                <tbody>
                                    ${result.results.map(row => `
                                        <tr>
                                            ${keys.map(key => `<td style="border: 1px solid #ddd; padding: 8px;">${row[key] !== undefined ? row[key] : ''}</td>`).join('')}
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `;
                    } else {
                        resultsHtml = `<pre>${JSON.stringify(result.results, null, 2)}</pre>`;
                    }
                    
                    // Reset button state
                    queryBtn.innerHTML = originalBtnText;
                    queryBtn.disabled = false;
                    
                    // Display the results
                    resultsDiv.innerHTML = `
                        <h3>Query Results</h3>
                        <div class="success-message" style="margin-bottom: 1rem;">
                            <span style="font-size: 1.25rem;">✓</span>
                            <span><strong>Success!</strong> Query processed successfully.</span>
                        </div>
                        
                        <h4>SQL Query</h4>
                        <pre>${result.sql_query}</pre>
                        
                        <h4>Reasoning</h4>
                        <p>${result.reasoning}</p>
                        
                        <h4>Execution Plan</h4>
                        <p>${result.execution_plan}</p>
                        
                        <h4>Results</h4>
                        ${resultsHtml}
                    `;
                    
                } catch (error) {
                    console.error('Error:', error);
                    resultsDiv.innerHTML = `
                        <div class="error-message">
                            <span style="font-size: 1.25rem;">⚠️</span>
                            <span><strong>Error:</strong> ${error.message}</span>
                        </div>
                    `;
                    
                    // Reset button state
                    queryBtn.innerHTML = originalBtnText;
                    queryBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True, port=5000)
