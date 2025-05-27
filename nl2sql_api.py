import os
import json
import sqlite3
import pandas as pd
import numpy as np
import yaml
import xmltodict
import shutil
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import openai
from openai import OpenAI
import time

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create temp directory if it doesn't exist
os.makedirs('temp', exist_ok=True)
os.makedirs('test', exist_ok=True)

# Custom JSON encoder to handle numpy types
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# API Routes
@app.route('/')
def health_check():
    """Health check endpoint for the API server."""
    return jsonify({
        'status': 'healthy',
        'service': 'nl2sql-api',
        'version': '1.0.0'
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Handle file upload and process the file based on its type.
    Returns a JSON response with the analysis results.
    """
    if 'file' not in request.files:
        response = json.dumps({'error': 'No file part'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    file = request.files['file']
    
    if file.filename == '':
        response = json.dumps({'error': 'No selected file'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    # Save the file to a temporary location
    timestamp = int(time.time())
    file_path = os.path.join('temp', f"{timestamp}_{file.filename}")
    file.save(file_path)
    
    try:
        # Analyze the file with LLM
        analysis_result = analyze_file_with_llm(file_path)
        
        # Process the file based on its type
        db_path = os.path.join('temp', f"{timestamp}_database.db")
        process_file(file_path, db_path)
        
        # Return the analysis result and paths
        response = {
            'success': True,
            'message': 'File uploaded and processed successfully',
            'analysis': analysis_result,
            'data_dict_path': file_path,
            'db_path': db_path
        }
        
        return json.dumps(response, cls=NpEncoder), 200, {'Content-Type': 'application/json'}
    
    except Exception as e:
        response = {
            'error': str(e)
        }
        return json.dumps(response, cls=NpEncoder), 500, {'Content-Type': 'application/json'}

@app.route('/api/query', methods=['POST'])
def process_query():
    """
    Process a natural language query and convert it to SQL.
    Returns a JSON response with the query results.
    """
    data = request.json
    
    if not data or 'query' not in data:
        response = {'error': 'No query provided'}
        return jsonify(response), 400
    
    query = data['query']
    db_path = data.get('db_path')
    data_dict_path = data.get('data_dict_path')
    
    if not db_path or not data_dict_path:
        response = {'error': 'Database path or data dictionary path not provided'}
        return jsonify(response), 400
    
    try:
        # Get table information from the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_info = {}
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            table_info[table_name] = [col[1] for col in columns]
        
        # Convert query to SQL using GPT-4.1 Nano
        sql_result = convert_to_sql(query, table_info, data_dict_path)
        
        # Execute the SQL query
        if sql_result.get('sql'):
            try:
                # Get the SQL query
                sql_query = sql_result['sql']
                
                # Fix table names in the query if needed
                for table_name in table_info.keys():
                    # Clean up table name to ensure it's valid SQL
                    clean_table_name = table_name.split('.')[0]  # Remove file extension if present
                    # Remove timestamp prefix if present (like 1748327704_)
                    if '_' in clean_table_name and clean_table_name.split('_')[0].isdigit():
                        clean_table_name = '_'.join(clean_table_name.split('_')[1:])
                    
                    # Replace the original table name with the cleaned one in the query
                    sql_query = sql_query.replace(f'"{table_name}"', f'"{clean_table_name}"')
                    sql_query = sql_query.replace(f'`{table_name}`', f'`{clean_table_name}`')
                    sql_query = sql_query.replace(f'[{table_name}]', f'[{clean_table_name}]')
                    sql_query = sql_query.replace(f' {table_name} ', f' {clean_table_name} ')
                
                # Execute the query
                df = pd.read_sql_query(sql_query, conn)
                records = df.to_dict('records')
                columns = df.columns.tolist()
                
                response = {
                    'success': True,
                    'query': query,
                    'sql': sql_result['sql'],
                    'reasoning': sql_result.get('reasoning', ''),
                    'columns': columns,
                    'data': records
                }
            except Exception as e:
                response = {
                    'success': False,
                    'query': query,
                    'sql': sql_result['sql'],
                    'reasoning': sql_result.get('reasoning', ''),
                    'error': f"Error executing SQL: {str(e)}"
                }
        else:
            response = {
                'success': False,
                'query': query,
                'error': sql_result.get('error', 'Failed to convert query to SQL')
            }
        
        conn.close()
        return jsonify(response)
    
    except Exception as e:
        response = {
            'success': False,
            'query': query,
            'error': str(e)
        }
        return jsonify(response), 500

@app.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    """
    Clear all uploaded and generated files from the temp directory.
    Returns a JSON response with the number of files removed.
    """
    try:
        count = 0
        for filename in os.listdir('temp'):
            file_path = os.path.join('temp', filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
                count += 1
        
        response = {
            'success': True,
            'message': f'Cache cleared successfully. {count} files removed'
        }
        return jsonify(response)
    
    except Exception as e:
        response = {
            'success': False,
            'error': str(e)
        }
        return jsonify(response), 500

# Helper Functions
def analyze_file_with_llm(file_path):
    """
    Analyze the file content using GPT-4.1 Nano to determine if it contains
    schema or actual data, and return a structured analysis response.
    """
    # Read the first few lines of the file to analyze
    file_ext = os.path.splitext(file_path)[1].lower()
    sample_content = ""
    
    try:
        if file_ext == '.csv':
            df = pd.read_csv(file_path, nrows=5)
            sample_content = df.to_csv(index=False)
        elif file_ext == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
            sample_content = json.dumps(data, indent=2)[:1000]  # First 1000 chars
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path, nrows=5)
            sample_content = df.to_csv(index=False)
        elif file_ext == '.xml':
            with open(file_path, 'r') as f:
                data = xmltodict.parse(f.read())
            sample_content = json.dumps(data, indent=2)[:1000]  # First 1000 chars
        elif file_ext in ['.yaml', '.yml']:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            sample_content = yaml.dump(data)[:1000]  # First 1000 chars
        else:
            return {
                'error': f'Unsupported file format: {file_ext}'
            }
    except Exception as e:
        return {
            'error': f'Error reading file: {str(e)}'
        }
    
    # Prepare the prompt for GPT
    prompt = f"""
    I have a data file with the following content (showing first few lines/records):
    
    {sample_content}
    
    Analyze this content and tell me:
    1. Is this a schema definition or actual data?
    2. What kind of information does this file contain?
    3. What are the key fields/columns and what do they represent?
    4. What types of questions would be interesting to ask about this data?
    
    Format your response as JSON with the following structure:
    {{"file_type": "schema" or "data", "description": "Brief description of what the file contains", "key_fields": [{{"name": "field_name", "description": "what this field represents"}}], "sample_questions": ["question 1", "question 2", "question 3"]}}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes file content to determine if it contains schema information or actual data."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        analysis = json.loads(response.choices[0].message.content)
        return analysis
    
    except Exception as e:
        return {
            'error': f'Error analyzing file with LLM: {str(e)}'
        }

def process_file(file_path, db_path):
    """
    Process the uploaded file and create a SQLite database.
    Supports CSV, JSON, XML, YAML, and Excel files.
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Read the file into a pandas DataFrame
    if file_ext == '.csv':
        df = pd.read_csv(file_path)
    elif file_ext == '.json':
        with open(file_path, 'r') as f:
            json_data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(json_data, list):
            # It's an array of objects
            df = pd.DataFrame(json_data)
        elif isinstance(json_data, dict):
            # Check if it's a nested structure with records
            if any(isinstance(v, list) for v in json_data.values()):
                # Find the key with a list value (assuming it's the data)
                for key, value in json_data.items():
                    if isinstance(value, list):
                        df = pd.DataFrame(value)
                        break
            else:
                # It's a single object, convert to a single row DataFrame
                df = pd.DataFrame([json_data])
        else:
            raise ValueError("Unsupported JSON structure")
    elif file_ext in ['.xls', '.xlsx']:
        df = pd.read_excel(file_path)
    elif file_ext == '.xml':
        with open(file_path, 'r') as f:
            xml_data = xmltodict.parse(f.read())
        
        # Convert XML to DataFrame (this is simplified and may need adjustments)
        # Find the first list in the nested structure
        def find_first_list(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        return value
                    result = find_first_list(value)
                    if result:
                        return result
            return None
        
        records = find_first_list(xml_data)
        if records:
            df = pd.DataFrame(records)
        else:
            # If no list found, use the whole structure as a single record
            df = pd.DataFrame([xml_data])
    elif file_ext in ['.yaml', '.yml']:
        with open(file_path, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        # Handle different YAML structures
        if isinstance(yaml_data, list):
            # It's an array of objects
            df = pd.DataFrame(yaml_data)
        elif isinstance(yaml_data, dict):
            # Check if it contains a list of records
            if any(isinstance(v, list) for v in yaml_data.values()):
                # Find the key with a list value
                for key, value in yaml_data.items():
                    if isinstance(value, list):
                        if all(isinstance(item, dict) for item in value):
                            df = pd.DataFrame(value)
                        else:
                            # Handle list of non-dict items
                            records = []
                            for i, item in enumerate(value):
                                record = {'id': i, 'value': item}
                                records.append(record)
                            df = pd.DataFrame(records)
                        break
            elif any(isinstance(v, dict) for v in yaml_data.values()):
                # It has nested dictionaries, flatten them
                records = []
                for key, value in yaml_data.items():
                    if isinstance(value, dict):
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
    
    # Get table name from file name without timestamp prefix
    base_name = os.path.basename(file_path).split('.')[0]
    
    # Remove timestamp prefix if present (like 1748327704_)
    if '_' in base_name and base_name.split('_')[0].isdigit():
        table_name = '_'.join(base_name.split('_')[1:])
    else:
        table_name = base_name
    
    # Write DataFrame to SQLite
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    conn.close()
    return True

def convert_to_sql(query, table_info, data_dict_path):
    """
    Convert a natural language query to SQL using GPT-4.1 Nano.
    Returns a dictionary with the SQL query and reasoning.
    """
    # Read a sample of the data to provide context
    file_ext = os.path.splitext(data_dict_path)[1].lower()
    sample_content = ""
    
    try:
        if file_ext == '.csv':
            df = pd.read_csv(data_dict_path, nrows=5)
            sample_content = df.to_csv(index=False)
        elif file_ext == '.json':
            with open(data_dict_path, 'r') as f:
                data = json.load(f)
            sample_content = json.dumps(data, indent=2)[:1000]
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(data_dict_path, nrows=5)
            sample_content = df.to_csv(index=False)
        elif file_ext == '.xml':
            with open(data_dict_path, 'r') as f:
                data = xmltodict.parse(f.read())
            sample_content = json.dumps(data, indent=2)[:1000]
        elif file_ext in ['.yaml', '.yml']:
            with open(data_dict_path, 'r') as f:
                data = yaml.safe_load(f)
            sample_content = yaml.dump(data)[:1000]
    except Exception as e:
        return {
            'error': f'Error reading data file: {str(e)}'
        }
    
    # Prepare the prompt for GPT
    tables_str = ""
    for table_name, columns in table_info.items():
        # Clean up table name to ensure it's valid SQL
        clean_table_name = table_name.split('.')[0]  # Remove file extension if present
        # Remove timestamp prefix if present (like 1748327704_)
        if '_' in clean_table_name and clean_table_name.split('_')[0].isdigit():
            clean_table_name = '_'.join(clean_table_name.split('_')[1:])
            
        tables_str += f"Table: {clean_table_name}\n"
        tables_str += f"Columns: {', '.join(columns)}\n\n"
    
    prompt = f"""
    I have a SQLite database with the following structure:
    
    {tables_str}
    
    Here's a sample of the data:
    {sample_content}
    
    Convert the following natural language query to SQL:
    "{query}"
    
    Provide your reasoning step by step, then the final SQL query.
    Format your response as JSON with the following structure:
    {{
        "reasoning": "Your step-by-step reasoning",
        "sql": "The SQL query"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are an AI assistant that converts natural language queries to SQL."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        return {
            'error': f'Error converting query to SQL: {str(e)}'
        }

if __name__ == '__main__':
    app.run(debug=True)
