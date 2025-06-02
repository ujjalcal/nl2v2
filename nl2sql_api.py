import os
import json
import sqlite3
import pandas as pd
import numpy as np
import yaml
import xmltodict
import shutil
import re
import uuid
import os
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from queue import Queue
import threading
from dotenv import load_dotenv
from openai import OpenAI
import time

# Import the master agent and query processor
from master_agent import MasterAgent
from agentic_processor import AgenticQueryProcessor

# Load environment variables
load_dotenv()

# Debug API key (show only first 10 chars for security)
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    masked_key = api_key[:10] + "..." if len(api_key) > 10 else "None"
    print(f"[API] API Key loaded (first 10 chars): {masked_key}")
else:
    print("[API] WARNING: No OpenAI API key found in environment variables")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

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

# Initialize the API server
def initialize():
    """Initialize the API server."""
    global query_processor, master_agent
    
    # Create temp directory if it doesn't exist
    os.makedirs('temp', exist_ok=True)
    
    # Initialize query processor
    query_processor = AgenticQueryProcessor()
    
    # Check if master agent is enabled via environment variable
    use_master_agent = os.environ.get('USE_MASTER_AGENT', 'false').lower() == 'true'
    
    # Initialize master agent if enabled
    if use_master_agent:
        master_agent = MasterAgent()
        print("Master agent initialized and ready")
    else:
        print("Master agent disabled, using legacy mode")

# Initialize on startup
initialize()

# Simple global events list for tracking agent activities
global_events = []

# Global variables
global_events = []
current_file_id = None
current_workflow_state = 'IDLE'
query_processor = None
master_agent = None

def agent_activity(agent_name, workflow_state, message, details=None):
    """Record real agent activity to the global events list."""
    global current_workflow_state, current_file_id, global_events
    
    # Update current workflow state
    current_workflow_state = workflow_state
    
    # Create event data
    event_data = {
        'file_id': current_file_id,
        'timestamp': int(time.time()),
        'agent': agent_name,
        'workflow_state': workflow_state,
        'message': message,
        'details': details or {}
    }
    
    # Log the agent activity
    print(f"Agent activity: {agent_name} - [{workflow_state}] - {message}")
    app.logger.info(f"Agent activity: {agent_name} - [{workflow_state}] - {message}")
    
    # Add to global events list (keep last 50 events)
    global_events.append(event_data)
    if len(global_events) > 50:
        global_events = global_events[-50:]
    
    return event_data

# API Routes
@app.route('/')
def health_check():
    """Health check endpoint for the API server."""
    return jsonify({
        'status': 'healthy',
        'service': 'nl2sql-api',
        'version': '1.0.0'
    })

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all agent activities."""
    global global_events
    
    # Get the timestamp parameter if provided
    timestamp = request.args.get('since', 0, type=int)
    
    # Filter events by timestamp if provided
    if timestamp > 0:
        filtered_events = [event for event in global_events if event['timestamp'] > timestamp]
    else:
        filtered_events = global_events
    
    return jsonify({
        'events': filtered_events,
        'current_state': current_workflow_state
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Handle file upload and process the file based on its type.
    Returns a JSON response with the analysis results.
    """
    try:
        # Initialize a new file processing session
        global current_file_id, global_events
        current_file_id = str(uuid.uuid4())
        
        # Clear previous events
        global_events = []
        
        # Check if file was uploaded
        if 'file' not in request.files:
            agent_activity('WorkflowOrchestratorAgent', 'ERROR', 'No file uploaded')
            response = json.dumps({'error': 'No file part'}, cls=NpEncoder)
            return response, 400, {'Content-Type': 'application/json'}
        
        file = request.files['file']
        
        # Check if file is empty
        if file.filename == '':
            agent_activity('WorkflowOrchestratorAgent', 'ERROR', 'No file selected')
            response = json.dumps({'error': 'No selected file'}, cls=NpEncoder)
            return response, 400, {'Content-Type': 'application/json'}
        
        # Workflow orchestrator starts the process
        agent_activity('WorkflowOrchestratorAgent', 'FILE_DROPPED', f'Starting to process file: {file.filename}')
        
        # File upload agent receives the file
        agent_activity('FileUploadAgent', 'FILE_DROPPED', f'Received file: {file.filename}')
        
        # Save the file to a temporary location
        timestamp = int(time.time())
        file_path = os.path.join('temp', f"{timestamp}_{secure_filename(file.filename)}")
        file.save(file_path)
        
        # File upload agent confirms file is saved
        agent_activity('FileUploadAgent', 'FILE_DROPPED', 'File saved successfully')
        
        # File classifier agent begins classification
        agent_activity('FileClassifierAgent', 'CLASSIFYING', 'Starting file classification')
        
        # Analyze the file with LLM for classification
        agent_activity('FileClassifierAgent', 'CLASSIFYING', 'Analyzing file content and structure')
        analysis_result = analyze_file_with_llm(file_path)
        agent_activity('FileClassifierAgent', 'CLASSIFIED', 'File classification complete', analysis_result)
        
        # Process the file based on its type
        db_path = os.path.join('temp', f"{timestamp}_database.db")
        is_schema_file = False
        data_dict_path = file_path
        
        # Start profiling
        agent_activity('DataProfilerAgent', 'PROFILING', 'Starting data profiling')
        
        # Check if this is a schema file with multiple tables
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
            if all(col in df.columns for col in ['TABLE_NAME', 'COLUMN_NAME', 'DATA_TYPE']):
                is_schema_file = True
                # Generate data dictionary path for schema file
                data_dict_path = os.path.splitext(file_path)[0] + "_dict.json"
                agent_activity('DataProfilerAgent', 'PROFILED', 'Schema file identified and profiled', {
                    'is_schema_file': True,
                    'tables_count': len(df['TABLE_NAME'].unique())
                })
            else:
                agent_activity('DataProfilerAgent', 'PROFILED', 'Data file profiled', {
                    'is_schema_file': False,
                    'rows_count': len(df),
                    'columns_count': len(df.columns)
                })
        else:
            agent_activity('DataProfilerAgent', 'PROFILED', 'Data file profiled')
        
        # Process the file based on whether it's a schema file or not
        if is_schema_file:
            # For schema files, we need to create the data dictionary
            agent_activity('DictionarySynthesizerAgent', 'DICT_DRAFTING', 'Creating draft data dictionary')
            df = pd.read_csv(file_path)
            
            # Process schema file with real agent activities
            process_schema_file(file_path, db_path, df)
            agent_activity('DictionarySynthesizerAgent', 'DICT_DRAFT', 'Data dictionary draft created')
            
            # Dictionary review (real agent activity)
            agent_activity('DictionaryReviewerAgent', 'DICT_REVIEWING', 'Reviewing data dictionary')
            
            # Simulate the review process (in a real system, this would be a separate agent)
            data_dict_exists = os.path.exists(os.path.splitext(file_path)[0] + "_dict.json")
            review_details = {
                'data_dictionary_exists': data_dict_exists,
                'review_status': 'approved' if data_dict_exists else 'failed'
            }
            agent_activity('DictionaryReviewerAgent', 'DICT_REVIEWED', 
                          'Data dictionary reviewed and approved' if data_dict_exists else 'Review failed - dictionary not found',
                          review_details)
            
            # Update the data_dict_path to point to the generated JSON file
            data_dict_path = os.path.splitext(file_path)[0] + "_dict.json"
            
            # Ready state
            agent_activity('WorkflowOrchestratorAgent', 'READY', 'Preparing for sample data generation')
            
            # Sample data generation
            agent_activity('SampleDataGeneratorAgent', 'BULK_LOADING', 'Generating realistic sample data')
            
            # Make sure the file exists
            if not os.path.exists(data_dict_path):
                # If the file doesn't exist, fall back to the original file path
                data_dict_path = file_path
                agent_activity('SampleDataGeneratorAgent', 'ERROR', 'Dictionary file not found, using original file')
            else:
                agent_activity('SampleDataGeneratorAgent', 'BULK_LOADED', 'Sample data generated successfully')
        else:
            # For regular data files
            agent_activity('WorkflowOrchestratorAgent', 'READY', 'Preparing database setup')
            agent_activity('DatabaseBuilderAgent', 'BULK_LOADING', 'Setting up database')
            process_file(file_path, db_path)
            agent_activity('DatabaseBuilderAgent', 'BULK_LOADED', 'Database setup complete')
        
        # Final progress update
        agent_activity('WorkflowOrchestratorAgent', 'DONE', 'Processing complete - Ready for queries')
        
        # Initialize or update the query processor with the new file paths
        global query_processor
        if query_processor is None:
            query_processor = AgenticQueryProcessor()
            agent_activity('API', 'INIT', 'Initializing new query processor')
        else:
            agent_activity('API', 'UPDATE', 'Updating existing query processor with new file paths')
        
        # Set the database and data dictionary paths for the query processor
        query_processor.db_path = db_path
        query_processor.data_dict_path = data_dict_path
        
        # Verify database connection was established
        if not query_processor.db_conn:
            agent_activity('API', 'CONNECTING', 'Connecting to database')
            query_processor._connect_to_db()
            if not query_processor.db_conn:
                agent_activity('API', 'ERROR', f'Failed to connect to database at {db_path}')
                raise ValueError(f"Failed to connect to database at {db_path}. Please check if the file exists and is valid.")
            else:
                agent_activity('API', 'CONNECTED', f'Successfully connected to database with {len(query_processor.db_conn.execute("SELECT name FROM sqlite_master WHERE type=\'table\'").fetchall())} tables')
        
        # Load data dictionary
        try:
            if os.path.exists(data_dict_path):
                agent_activity('API', 'LOADING', 'Loading data dictionary')
                query_processor._load_data_dictionary(data_dict_path)
                agent_activity('API', 'LOADED', 'Data dictionary loaded successfully')
            else:
                agent_activity('API', 'WARNING', f'Data dictionary file not found at {data_dict_path}')
        except Exception as dict_error:
            agent_activity('API', 'ERROR', f'Error loading data dictionary: {str(dict_error)}')
            print(f"Warning: Error loading data dictionary: {str(dict_error)}")
            # Continue despite dictionary error - we can still query the database
        
        # Return the analysis result and paths
        response = {
            'success': True,
            'message': 'File uploaded and processed successfully',
            'analysis': analysis_result,
            'is_schema_file': is_schema_file,
            'data_dict_path': data_dict_path,
            'db_path': db_path,
            'file_id': current_file_id
        }
        
        return json.dumps(response, cls=NpEncoder), 200, {'Content-Type': 'application/json'}
    
    except Exception as e:
        response = {
            'error': str(e)
        }
        return json.dumps(response, cls=NpEncoder), 500, {'Content-Type': 'application/json'}

@app.route('/api/query', methods=['POST'])
def process_query():
    """Process a natural language query."""
    try:
        global query_processor, master_agent
        data = request.json
        nl_query = data.get('query', '')
        
        # Log query
        print(f"Processing query: {nl_query}")
        agent_activity('API', 'QUERY_RECEIVED', f"Query received: {nl_query}")
        
        # Check if master agent is enabled via environment variable
        use_master_agent = os.environ.get('USE_MASTER_AGENT', 'false').lower() == 'true'
        
        # Verify query processor is initialized
        if not use_master_agent and (query_processor is None or not hasattr(query_processor, 'db_path') or not query_processor.db_path):
            agent_activity('API', 'ERROR', "Query processor not initialized or database not set")
            return jsonify({
                'success': False,
                'error': "Query processor not initialized. Please upload a file first."
            })
        
        # Process the query using master agent if enabled, otherwise use legacy processor
        if use_master_agent and master_agent is not None:
            # Create a goal for processing the query
            goal_id = master_agent.create_goal('process_query', {'query': nl_query})
            agent_activity('MasterAgent', 'PROCESSING', f"Processing query via goal {goal_id}")
            
            # Execute the goal
            result = master_agent.execute_goal(goal_id)
            
            # Add goal_id to the result
            result['goal_id'] = goal_id
        else:
            # Use legacy query processor
            agent_activity('AgenticQueryProcessor', 'PROCESSING', "Processing query via agentic processor")
            try:
                result = query_processor.process_query(nl_query)
                agent_activity('AgenticQueryProcessor', 'PROCESSED', "Query processed by agentic processor")
            except Exception as processor_error:
                agent_activity('AgenticQueryProcessor', 'ERROR', f"Error in query processor: {str(processor_error)}")
                raise processor_error
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            result = {
                'success': True,
                'message': str(result),
                'type': 'generic'
            }
        
        # Add SQL query to response if available
        if 'execution_plan' in result and result['execution_plan']:
            for step in result['execution_plan']:
                if step.get('action') == 'execute_sql' and 'query' in step:
                    result['sql'] = step['query']
                    break
        
        # Handle results based on format
        if 'results' in result:
            # If results is a list of dictionaries (common SQLite result format)
            if isinstance(result['results'], list) and len(result['results']) > 0 and isinstance(result['results'][0], dict):
                # Extract column names from the first result
                if result['results']:
                    columns = list(result['results'][0].keys())
                    # Convert to rows format expected by frontend
                    rows = [[row.get(col) for col in columns] for row in result['results']]
                    result['columns'] = columns
                    result['rows'] = rows
                else:
                    # No results
                    result['columns'] = []
                    result['rows'] = []
                # Remove the original results to avoid duplication
                del result['results']
            # Handle dictionary format (column name -> list of values)
            elif isinstance(result['results'], dict):
                columns = list(result['results'].keys())
                if columns and len(result['results'][columns[0]]) > 0:
                    # Transpose the data from column-oriented to row-oriented
                    rows = []
                    for i in range(len(result['results'][columns[0]])):
                        row = [result['results'][col][i] if i < len(result['results'][col]) else None for col in columns]
                        rows.append(row)
                    result['columns'] = columns
                    result['rows'] = rows
                else:
                    # Empty results
                    result['columns'] = columns
                    result['rows'] = []
                del result['results']
        
        # Ensure success flag is set
        if 'success' not in result:
            result['success'] = True
        
        # Log success
        agent_activity('API', 'QUERY_PROCESSED', "Query processed successfully")
        
        return jsonify(result)
    
    except Exception as e:
        # Log error
        error_message = str(e)
        print(f"Error processing query: {error_message}")
        agent_activity('API', 'ERROR', f"Error processing query: {error_message}")
        
        # Include stack trace in development
        import traceback
        stack_trace = traceback.format_exc()
        print(f"Stack trace: {stack_trace}")
        
        return jsonify({
            'success': False,
            'error': error_message,
            'details': "Please make sure you've uploaded a file before submitting queries."
        })

# Add new API endpoints for goal management
@app.route('/api/goals', methods=['GET'])
def get_goals():
    """Get all goals."""
    global master_agent
    
    # Check if master agent is enabled via environment variable
    use_master_agent = os.environ.get('USE_MASTER_AGENT', 'false').lower() == 'true'
    
    if not use_master_agent or master_agent is None:
        return jsonify({
            'success': False,
            'error': 'Master agent is not enabled'
        })
    
    try:
        goals = master_agent.get_all_goals()
        return jsonify({
            'success': True,
            'goals': goals
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/goals/<goal_id>', methods=['GET'])
def get_goal(goal_id):
    """Get a specific goal by ID."""
    global master_agent
    
    # Check if master agent is enabled via environment variable
    use_master_agent = os.environ.get('USE_MASTER_AGENT', 'false').lower() == 'true'
    
    if not use_master_agent or master_agent is None:
        return jsonify({
            'success': False,
            'error': 'Master agent is not enabled'
        })
    
    try:
        goal = master_agent.goal_tracker.get_goal(goal_id)
        return jsonify({
            'success': True,
            'goal': goal
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# This duplicate execute_goal endpoint was removed to fix the route conflict

@app.route('/api/goals', methods=['POST'])
def create_goal():
    """Create a new goal."""
    if not use_master_agent:
        return jsonify({
            'success': False,
            'error': 'Master agent is not enabled'
        })
    
    try:
        data = request.json
        template_name = data.get('template')
        parameters = data.get('parameters', {})
        
        if not template_name:
            return jsonify({
                'success': False,
                'error': 'No template name provided'
            })
        
        goal_id = master_agent.create_goal(template_name, parameters)
        return jsonify({
            'success': True,
            'goal_id': goal_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# The duplicate execute_goal endpoint was removed to fix the route conflict
# This function was previously defined at line 455-479

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
def clean_yaml_response(content):
    """
    Clean up YAML content by removing code block markers if present.
    This function only handles removing markdown code block markers and does not
    attempt to fix or modify the YAML content itself.
    """
    if not content:
        return content
        
    # Print the raw content for debugging
    print(f"\n[DEBUG] Raw LLM response before cleaning:\n{content}")
        
    # Handle code blocks with or without language specifiers
    if '```' in content:
        # Extract content between code block markers
        pattern = r'```(?:yaml|yml)?\s*([\s\S]*?)```'
        matches = re.findall(pattern, content)
        if matches:
            # Just take the first match - we expect only one YAML block
            content = matches[0].strip()
        else:
            # If regex fails, just remove the markers directly
            content = content.replace('```yaml', '').replace('```yml', '').replace('```', '').strip()
    
    # Just trim whitespace, no other modifications
    content = content.strip()
    
    # Print the cleaned content for debugging
    print(f"\n[DEBUG] Cleaned YAML content:\n{content}")
    
    return content


def clean_sql_query(sql_query):
    """
    Clean up SQL query by removing comments and handling CTEs properly.
    
    Args:
        sql_query: The SQL query to clean
        
    Returns:
        Cleaned SQL query string
    """
    if not sql_query:
        return sql_query
    
    # Remove SQL comments (both -- and /* */ style)
    lines = []
    for line in sql_query.split('\n'):
        # Remove inline comments starting with --
        comment_pos = line.find('--')
        if comment_pos >= 0:
            line = line[:comment_pos].strip()
        
        # Skip empty lines after comment removal
        if line.strip():
            lines.append(line)
    
    # Join lines back together
    cleaned_sql = ' '.join(lines)
    
    # Handle CTEs - if there's a WITH clause, make sure it's at the beginning of the query
    if ' WITH ' in cleaned_sql.upper():
        # Extract the CTE part and the main query
        parts = cleaned_sql.upper().split(' WITH ', 1)
        if len(parts) > 1 and parts[0].strip():
            # There's content before WITH, which is invalid in SQLite
            # Get the original case version
            original_parts = cleaned_sql.split(' WITH ', 1)
            if len(original_parts) > 1:
                # Remove any content before WITH and use just the CTE
                cleaned_sql = 'WITH ' + original_parts[1]
        
    return cleaned_sql


def generate_result_summary(query, sql, records, columns):
    """
    Generate a natural language summary of SQL query results using GPT-4.1-nano.
    
    Args:
        query: The original natural language query
        sql: The SQL query that was executed
        records: The query results as a list of dictionaries
        columns: The column names from the results
        
    Returns:
        A natural language summary of the results
    """
    # If no results, return a simple message
    if not records:
        return "No results were found for your query."
    
    # Prepare a sample of the results for the LLM
    result_sample = records[:5]  # Take up to 5 records to avoid token limits
    total_records = len(records)
    
    # Calculate some basic statistics if there are numeric columns
    stats = {}
    for col in columns:
        # Check if this column has numeric values
        numeric_values = []
        for record in records:
            value = record.get(col)
            if isinstance(value, (int, float)) and value is not None:
                numeric_values.append(value)
        
        if numeric_values:
            stats[col] = {
                'min': min(numeric_values),
                'max': max(numeric_values),
                'avg': sum(numeric_values) / len(numeric_values),
                'count': len(numeric_values)
            }
    
    # Create prompt for GPT
    prompt = f"""
    I need you to summarize the results of a database query in a clear, concise way.
    
    Original question: "{query}"
    
    SQL query used: "{sql}"
    
    The query returned {total_records} results with these columns: {', '.join(columns)}
    
    Here's a sample of the results:
    {json.dumps(result_sample, indent=2)}
    
    Statistics for numeric columns:
    {json.dumps(stats, indent=2)}
    
    Please provide a concise, natural language summary of these results that directly answers the original question.
    Focus on key insights, patterns, or notable findings. Keep your response under 3-4 sentences.
    """
    
    try:
        # Query GPT-4.1-nano for the summary
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are an AI assistant that specializes in summarizing database query results in clear, concise language."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        
        # Return the summary
        return response.choices[0].message.content.strip()
    except Exception as e:
        # If there's an error, return a basic summary
        print(f"Error generating summary: {str(e)}")
        return f"Query returned {total_records} results with columns: {', '.join(columns)}."

# Analysis Functions
def analyze_file_with_llm(file_path):
    """
    Analyze the file content using GPT-4.1 Nano to determine if it contains
    schema or actual data, and return a structured analysis response.
    Handles schema files with multiple table definitions.
    """
    # Read the first few lines of the file to analyze
    file_ext = os.path.splitext(file_path)[1].lower()
    sample_content = ""
    is_schema_file = False
    tables_info = {}
    
    try:
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
            # Check if this is a schema definition file with multiple tables
            if all(col in df.columns for col in ['TABLE_NAME', 'COLUMN_NAME', 'DATA_TYPE']):
                is_schema_file = True
                # Group by table name to get table structure
                for table_name, group in df.groupby('TABLE_NAME'):
                    tables_info[table_name] = {
                        'columns': group['COLUMN_NAME'].tolist(),
                        'data_types': dict(zip(group['COLUMN_NAME'], group['DATA_TYPE']))
                    }
                sample_content = df.head(20).to_csv(index=False)
            else:
                sample_content = df.head(5).to_csv(index=False)
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
    
    # If it's a schema file with multiple tables, create a custom analysis
    if is_schema_file and tables_info:
        tables_summary = []
        for table_name, info in tables_info.items():
            tables_summary.append({
                'name': table_name,
                'columns_count': len(info['columns']),
                'columns': info['columns'][:5] + ['...'] if len(info['columns']) > 5 else info['columns']
            })
        
        # Create sample questions based on the tables
        sample_questions = [
            f"What is the total count of records in {tables_summary[0]['name']}?",
            f"What are the unique values of {tables_summary[0]['columns'][0]} in {tables_summary[0]['name']}?"
        ]
        
        # If we have multiple tables, add a join question
        if len(tables_summary) > 1:
            sample_questions.append(f"What is the relationship between {tables_summary[0]['name']} and {tables_summary[1]['name']}?")
        
        return {
            'file_type': 'schema',
            'description': f'Schema definition file containing {len(tables_info)} tables',
            'tables': tables_summary,
            'sample_questions': sample_questions
        }
    
    # For non-schema files or if schema detection failed, use GPT to analyze
    prompt = f"""
    I have a data file with the following content (showing first few lines/records):
    
    {sample_content}
    
    Analyze this content and tell me:
    1. Is this a schema definition or actual data?
    2. What kind of information does this file contain?
    3. What are the key fields/columns and what do they represent?
    4. What types of questions would be interesting to ask about this data?
    
    Format your response as YAML with the following structure:
    ```yaml
    file_type: schema or data
    description: Brief description of what the file contains
    key_fields:
      - name: field_name
        description: what this field represents
    sample_questions:
      - question 1
      - question 2
      - question 3
    ```
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes file content to determine if it contains schema information or actual data. Respond in YAML format."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Get the response content and clean it
        content = clean_yaml_response(response.choices[0].message.content)
        
        # Parse YAML response
        analysis = yaml.safe_load(content)
        return analysis
    
    except Exception as e:
        return {
            'error': f'Error analyzing file with LLM: {str(e)}'
        }

def process_file(file_path, db_path):
    """
    Process the uploaded file and create a SQLite database.
    Supports CSV, JSON, XML, YAML, and Excel files.
    Also handles schema files with multiple table definitions.
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Note: Schema file detection and processing is now handled in the upload_file function
    # This function now only processes regular data files
    
    # If not a schema file, process as regular data file
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
    Handles multiple tables and relationships between them.
    """
    # Read a sample of the data to provide context
    file_ext = os.path.splitext(data_dict_path)[1].lower()
    sample_content = ""
    is_schema_file = False
    tables_data = {}
    
    try:
        # Check if this is a schema file with multiple tables
        if file_ext == '.csv':
            df = pd.read_csv(data_dict_path)
            if all(col in df.columns for col in ['TABLE_NAME', 'COLUMN_NAME', 'DATA_TYPE']):
                is_schema_file = True
                # Extract db_path from data_dict_path (assuming they're in the same directory)
                db_dir = os.path.dirname(data_dict_path)
                db_name = os.path.basename(data_dict_path).split('.')[0]
                if '_' in db_name and db_name.split('_')[0].isdigit():
                    timestamp = db_name.split('_')[0]
                    db_path = os.path.join(db_dir, f"{timestamp}_database.db")
                else:
                    db_path = os.path.join(db_dir, "database.db")
                
                # Get sample data for each table from the database
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                for table_name in table_info.keys():
                    try:
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
                        columns = [description[0] for description in cursor.description]
                        rows = cursor.fetchall()
                        
                        # Format as CSV-like string
                        table_sample = ",".join(columns) + "\n"
                        for row in rows:
                            table_sample += ",".join([str(val) for val in row]) + "\n"
                        
                        tables_data[table_name] = table_sample
                    except Exception as e:
                        print(f"Error getting sample data for table {table_name}: {str(e)}")
                
                conn.close()
                
                # Use the schema file as sample content if we couldn't get data
                if not tables_data:
                    sample_content = df.head(10).to_csv(index=False)
            else:
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
        tables_str += f"Columns: {', '.join(columns)}\n"
        
        # Add sample data for this table if available
        if table_name in tables_data:
            tables_str += f"Sample data:\n{tables_data[table_name]}\n"
        
        tables_str += "\n"
    
    # Add potential relationships between tables
    if len(table_info) > 1:
        relationships_str = identify_potential_relationships(table_info)
        if relationships_str:
            tables_str += f"Potential relationships between tables:\n{relationships_str}\n"
    
    prompt = f"""
    I have a SQLite database with the following structure:
    
    {tables_str}
    
    {'Here\'s a sample of the data:' if not is_schema_file else ''}
    {sample_content if not is_schema_file else ''}
    
    Convert the following natural language query to SQL:
    "{query}"
    
    Provide your reasoning step by step, then the final SQL query.
    Format your response as YAML with the following structure:
    ```yaml
    reasoning: |
      Your step-by-step reasoning here
      Use multiple lines with proper indentation
    sql: |
      The SQL query here
      Use proper SQL syntax
    ```
    
    CRITICAL INSTRUCTIONS:
    1. Your response MUST be valid YAML format
    2. Use the pipe character (|) for multi-line text as shown above
    3. Maintain proper indentation for multi-line text (2 spaces)
    4. Do not include any text outside the YAML structure
    5. Do not include the ```yaml and ``` markers in your actual response
    6. Both 'reasoning' and 'sql' keys are required
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            temperature=0.3,  # Lower temperature for more consistent formatting
            messages=[
                {"role": "system", "content": """You are an AI assistant that converts natural language queries to SQL. 
            
                IMPORTANT: You must respond in valid YAML format with the following structure:
                reasoning: | 
                  (multi-line reasoning with proper indentation)
                sql: |
                  (SQL query with proper indentation)
                  
                Use the pipe character (|) for multi-line strings and maintain proper indentation.
                Both 'reasoning' and 'sql' keys are required.
                Do not include any text outside this YAML structure.
                Do not include markdown code block markers (```yaml) in your response."""},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Get the response content and clean it
        content = clean_yaml_response(response.choices[0].message.content)
        
        # Get the raw response for debugging
        print(f"\n[DEBUG] Raw YAML content to parse:\n{content}")
        
        # Parse YAML response with strict validation - no fallbacks
        result = yaml.safe_load(content)
        
        # Validate that we have the required structure
        if not isinstance(result, dict):
            raise ValueError(f"Expected dictionary response, got {type(result)}")
            
        if 'sql' not in result:
            raise ValueError("Missing 'sql' key in response")
            
        if 'reasoning' not in result:
            raise ValueError("Missing 'reasoning' key in response")
            
        return result
    
    except Exception as e:
        return {
            'error': f'Error converting query to SQL: {str(e)}'
        }

def identify_potential_relationships(table_info):
    """
    Identify potential relationships between tables based on column names.
    
    Args:
        table_info: Dictionary mapping table names to their columns
    
    Returns:
        String describing potential relationships
    """
    relationships = []
    
    # Get all tables and their columns
    tables = list(table_info.keys())
    
    # Look for common column names that might indicate relationships
    for i in range(len(tables)):
        for j in range(i+1, len(tables)):
            table1 = tables[i]
            table2 = tables[j]
            columns1 = table_info[table1]
            columns2 = table_info[table2]
            
            # Find common columns
            common_columns = set(columns1).intersection(set(columns2))
            
            # Look for ID columns that might indicate relationships
            for col in common_columns:
                if col.lower().endswith('id') or col.lower() == 'id':
                    relationships.append(f"{table1}.{col} may join with {table2}.{col}")
            
            # Look for columns in table1 that might reference table2
            for col in columns1:
                # Check if column name contains the name of table2 (e.g., customer_id in orders table)
                if table2.lower() in col.lower() and col.lower().endswith('id'):
                    relationships.append(f"{table1}.{col} may reference {table2}")
            
            # Look for columns in table2 that might reference table1
            for col in columns2:
                # Check if column name contains the name of table1
                if table1.lower() in col.lower() and col.lower().endswith('id'):
                    relationships.append(f"{table2}.{col} may reference {table1}")
    
    return "\n".join(relationships) if relationships else ""

def process_schema_file(file_path, db_path, df):
    """
    Process a schema definition file and create tables with sample data.
    Also generates a comprehensive data dictionary using LLM and uses it
    to create realistic sample data.
    
    Args:
        file_path: Path to the schema file
        db_path: Path to the SQLite database to create
        df: DataFrame containing the schema definition
    
    Returns:
        True if successful
    """
    # Group by table name
    tables = {}
    for _, row in df.iterrows():
        table_name = row['TABLE_NAME']
        column_name = row['COLUMN_NAME']
        data_type = row['DATA_TYPE']
        
        if table_name not in tables:
            tables[table_name] = []
        
        column_info = {
            "name": column_name,
            "type": data_type,
            "ordinal_position": row.get('ORDINAL_POSITION', 0)
        }
        
        tables[table_name].append(column_info)
    
    # Generate data dictionary using LLM first
    print(f"\n[DEBUG] Generating data dictionary for schema with {len(tables)} tables")
    agent_activity('DictionarySynthesizerAgent', 'DICT_DRAFTING', f'Creating dictionary for {len(tables)} tables')
    data_dict = generate_data_dictionary_for_schema(tables)
    print(f"[DEBUG] Data dictionary generated with keys: {list(data_dict.keys())}")
    if 'tables' in data_dict:
        print(f"[DEBUG] Tables in data dictionary: {list(data_dict['tables'].keys())}")
    
    # Save data dictionary to file
    data_dict_path = os.path.splitext(file_path)[0] + "_dict.json"
    print(f"[DEBUG] Saving data dictionary to: {data_dict_path}")
    with open(data_dict_path, 'w') as f:
        json.dump(data_dict, f, indent=2, cls=NpEncoder)
    print(f"[DEBUG] Data dictionary saved successfully")
    agent_activity('DictionarySynthesizerAgent', 'DICT_DRAFT', 'Data dictionary created successfully')
    
    # Create SQLite database
    conn = sqlite3.connect(db_path)
    
    # Create tables and generate sample data for each using the data dictionary
    for table_name, columns in tables.items():
        # Sort columns by ordinal position if available
        columns.sort(key=lambda x: x.get("ordinal_position", 0))
        
        # Create table
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        column_defs = []
        
        for col in columns:
            col_name = col["name"]
            col_type = map_data_type_to_sqlite(col["type"])
            column_defs.append(f"    {col_name} {col_type}")
        
        create_table_sql += ",\n".join(column_defs)
        create_table_sql += "\n);"
        
        # Execute the CREATE TABLE statement without try-except to allow errors to propagate
        conn.execute(create_table_sql)
        
        # Generate sample data using the data dictionary (5 rows per table)
        print(f"\n[DEBUG] Generating sample data for table: {table_name}")
        print(f"[DEBUG] Using data dictionary with keys: {list(data_dict.keys())}")
        if 'tables' in data_dict and table_name in data_dict['tables']:
            print(f"[DEBUG] Table info available in data dictionary")
        else:
            print(f"[DEBUG] WARNING: Table {table_name} not found in data dictionary tables: {list(data_dict.get('tables', {}).keys())}")
        
        # Generate sample data with NO FALLBACKS - let errors propagate
        print(f"\n[DEBUG] Generating realistic sample data for table: {table_name}")
        print(f"[DEBUG] Number of columns: {len(columns)}")
        print(f"[DEBUG] Data dict keys: {list(data_dict.keys())}")
        
        # Show table description if available
        if 'tables' in data_dict and table_name in data_dict['tables'] and 'table_description' in data_dict['tables'][table_name]:
            print(f"[DEBUG] Found table in data dictionary. Table description: {data_dict['tables'][table_name]['table_description']}")
        
        # Call LLM for sample data generation - no try/except to allow errors to propagate
        print(f"\n[DEBUG] Sending prompt to LLM for table {table_name}")
        agent_activity('SampleDataGeneratorAgent', 'BULK_LOADING', f'Generating sample data for table {table_name}')
        sample_data = generate_realistic_sample_data(table_name, columns, data_dict, 5)
        
        # Insert sample data
        if sample_data:
            print(f"[DEBUG] Successfully generated {len(sample_data)} rows of sample data")
            agent_activity('DatabaseBuilderAgent', 'BULK_LOADING', f'Creating table {table_name} with {len(sample_data)} rows')
            col_names = [col["name"] for col in columns]
            placeholders = ", ".join(["?" for _ in col_names])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({placeholders})"
            
            for row in sample_data:
                conn.execute(insert_sql, row)
    
    conn.commit()
    conn.close()
    
    # Emit final event for schema processing completion
    agent_activity('DatabaseBuilderAgent', 'BULK_LOADED', f'Successfully created database with {len(tables)} tables')
    
    return True

def generate_data_dictionary_for_schema(tables):
    """
    Generate a comprehensive data dictionary for schema tables using LLM.
    
    Args:
        tables: Dictionary mapping table names to their column definitions
    
    Returns:
        Data dictionary object
    """
    # Initialize the data dictionary
    data_dict = {
        "dataset_name": "multi_table_schema",
        "description": "Schema with multiple related tables",
        "tables": {}
    }
    
    # Process each table
    for table_name, columns in tables.items():
        # Prepare column information for LLM
        columns_info = ""
        for col in columns:
            columns_info += f"Column: {col['name']}, Type: {col['type']}\n"
        
        # Create prompt for GPT
        prompt = f"""
        I have a database table with the following structure:
        
        Table: {table_name}
        {columns_info}
        
        Please analyze this table structure and provide:
        1. A description of what this table likely represents
        2. For each column, provide:
           - A description of what the column represents
           - Whether it's likely categorical
           - Possible constraints
           - Synonyms for the column name
           - Potential relationships with other columns
        
        Format your response as YAML with the following structure:
        ```yaml
        table_description: Description of the table
        columns:
          column_name1:
            description: What this column represents
            categorical: true/false
            constraints: Any constraints (e.g., "positive numbers only")
            synonyms: [synonym1, synonym2]
          column_name2:
            ...
        ```
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that specializes in database schema analysis. Respond in YAML format."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Get the response content and clean it
            content = clean_yaml_response(response.choices[0].message.content)
            
            try:
                # Parse YAML response
                table_dict = yaml.safe_load(content)
                
                # Validate the structure
                if not isinstance(table_dict, dict):
                    raise ValueError("LLM response is not a valid dictionary")
                
                # Ensure required keys exist
                if 'table_description' not in table_dict:
                    table_dict['table_description'] = f"Table containing {table_name} data"
                
                if 'columns' not in table_dict or not isinstance(table_dict['columns'], dict):
                    table_dict['columns'] = {}
                
                # Ensure all columns have entries
                for col in columns:
                    col_name = col["name"]
                    if col_name not in table_dict['columns']:
                        table_dict['columns'][col_name] = {
                            "description": f"{col_name} of type {col['type']}",
                            "categorical": col['type'].upper() in ['TEXT', 'VARCHAR', 'CHAR', 'STRING'],
                            "constraints": "",
                            "synonyms": [col_name.replace("_", " ")]
                        }
                
                # Add to data dictionary
                data_dict["tables"][table_name] = table_dict
                
            except Exception as yaml_error:
                print(f"Error parsing YAML for table {table_name}: {str(yaml_error)}")
                # Add basic information if YAML parsing fails
                data_dict["tables"][table_name] = {
                    "table_description": f"Table containing {table_name} data",
                    "columns": {col["name"]: {
                        "description": f"{col['name']} of type {col['type']}",
                        "categorical": col['type'].upper() in ['TEXT', 'VARCHAR', 'CHAR', 'STRING'],
                        "constraints": "",
                        "synonyms": [col["name"].replace("_", " ")]
                    } for col in columns}
                }
            
        except Exception as e:
            print(f"Error generating data dictionary for table {table_name}: {str(e)}")
            # Add basic information if LLM fails
            data_dict["tables"][table_name] = {
                "table_description": f"Table containing {table_name} data",
                "columns": {col["name"]: {
                    "description": f"{col['name']} of type {col['type']}",
                    "categorical": col['type'].upper() in ['TEXT', 'VARCHAR', 'CHAR', 'STRING'],
                    "constraints": "",
                    "synonyms": [col["name"].replace("_", " ")]
                } for col in columns}
            }
    
    # Add relationships between tables
    data_dict["relationships"] = identify_relationships_for_dict(tables)
    
    return data_dict

def identify_relationships_for_dict(tables):
    """
    Identify relationships between tables for the data dictionary.
    
    Args:
        tables: Dictionary mapping table names to their column definitions
    
    Returns:
        List of relationship dictionaries
    """
    relationships = []
    
    # Get all tables and their columns
    table_names = list(tables.keys())
    
    # Look for common column names that might indicate relationships
    for i in range(len(table_names)):
        for j in range(i+1, len(table_names)):
            table1 = table_names[i]
            table2 = table_names[j]
            columns1 = [col["name"] for col in tables[table1]]
            columns2 = [col["name"] for col in tables[table2]]
            
            # Find common columns
            common_columns = set(columns1).intersection(set(columns2))
            
            # Look for ID columns that might indicate relationships
            for col in common_columns:
                if col.lower().endswith('id') or col.lower() == 'id':
                    relationships.append({
                        "type": "join",
                        "table1": table1,
                        "table2": table2,
                        "column": col,
                        "description": f"{table1}.{col} may join with {table2}.{col}"
                    })
            
            # Look for columns in table1 that might reference table2
            for col in columns1:
                # Check if column name contains the name of table2 (e.g., customer_id in orders table)
                if table2.lower() in col.lower() and col.lower().endswith('id'):
                    relationships.append({
                        "type": "reference",
                        "from_table": table1,
                        "to_table": table2,
                        "column": col,
                        "description": f"{table1}.{col} may reference {table2}"
                    })
            
            # Look for columns in table2 that might reference table1
            for col in columns2:
                # Check if column name contains the name of table1
                if table1.lower() in col.lower() and col.lower().endswith('id'):
                    relationships.append({
                        "type": "reference",
                        "from_table": table2,
                        "to_table": table1,
                        "column": col,
                        "description": f"{table2}.{col} may reference {table1}"
                    })
    
    return relationships

def map_data_type_to_sqlite(data_type):
    """
    Map data types from schema to SQLite data types.
    
    Args:
        data_type: Original data type from schema
    
    Returns:
        SQLite data type
    """
    data_type = data_type.upper()
    
    if data_type in ['TEXT', 'VARCHAR', 'CHAR', 'STRING']:
        return 'TEXT'
    elif data_type in ['NUMBER', 'INT', 'INTEGER', 'BIGINT', 'SMALLINT']:
        return 'INTEGER'
    elif data_type in ['FLOAT', 'DOUBLE', 'DECIMAL', 'REAL']:
        return 'REAL'
    elif data_type in ['DATE', 'DATETIME', 'TIMESTAMP']:
        return 'TEXT'
    elif data_type in ['BOOLEAN', 'BOOL']:
        return 'INTEGER'
    elif data_type in ['BLOB', 'BINARY']:
        return 'BLOB'
    else:
        return 'TEXT'  # Default to TEXT for unknown types

def generate_realistic_sample_data(table_name, columns, data_dict, num_rows=5):
    """
    Generate realistic sample data for a table based on the data dictionary using LLM.
    No fallback mechanisms - will raise errors if LLM generation fails.
    
    Args:
        table_name: Name of the table
        columns: List of column definitions
        data_dict: Data dictionary with table and column information
        num_rows: Number of sample rows to generate
    
    Returns:
        List of sample data rows
    """
    # Prepare table description
    table_description = f"Table containing {table_name} data"
    if 'tables' in data_dict and table_name in data_dict['tables']:
        table_dict = data_dict['tables'][table_name]
        if 'table_description' in table_dict:
            table_description = table_dict['table_description']
    
    # Prepare column information
    columns_info = []
    for col in columns:
        col_name = col["name"]
        col_type = col["type"]
        
        # Get column description if available
        description = f"{col_name} of type {col_type}"
        categorical = col_type.upper() in ['TEXT', 'VARCHAR', 'CHAR', 'STRING']
        constraints = ""
        synonyms = [col_name.replace("_", " ")]
        
        if 'tables' in data_dict and table_name in data_dict['tables']:
            table_dict = data_dict['tables'][table_name]
            if 'columns' in table_dict and col_name in table_dict['columns']:
                col_info = table_dict['columns'][col_name]
                if 'description' in col_info:
                    description = col_info['description']
                if 'constraints' in col_info:
                    constraints = col_info['constraints']
                if 'categorical' in col_info:
                    categorical = col_info['categorical']
                if 'synonyms' in col_info and col_info['synonyms']:
                    synonyms = col_info['synonyms']
        
        columns_info.append({
            "name": col_name,
            "type": col_type,
            "description": description,
            "categorical": categorical,
            "constraints": constraints,
            "synonyms": synonyms
        })
    
    # Format column info for the prompt
    columns_text = ""
    for col_info in columns_info:
        columns_text += f"Column: {col_info['name']}, Type: {col_info['type']}\n"
        columns_text += f"Description: {col_info['description']}\n"
        if col_info['constraints']:
            columns_text += f"Constraints: {col_info['constraints']}\n"
        columns_text += f"Categorical: {col_info['categorical']}\n\n"
    
    # Create a list of column names for reference
    column_names = [col['name'] for col in columns]
    column_types = [col['type'] for col in columns]
    
    # Create prompt for GPT with detailed instructions
    prompt = f"""
    Generate {num_rows} rows of REALISTIC sample data for a database table with the following structure:
    
    Table: {table_name}
    Description: {table_description}
    CRITICAL: This table has EXACTLY {len(columns)} columns - no more, no less.
    
    Columns (in exact order):
    {columns_text}
    
    Your response MUST be a valid JSON array of arrays, where each inner array represents one row of data.
    CRITICAL REQUIREMENT: Each row MUST have EXACTLY {len(columns)} values in the EXACT order of columns listed above.
    
    Here is the exact list of {len(columns)} column names in order:
    {column_names}
    
    And their corresponding types:
    {column_types}
    
    Example format for this table with {len(columns)} columns:
    [
      [value1_for_col1, value2_for_col2, ..., value{len(columns)}_for_col{len(columns)}],
      [value1_for_col1, value2_for_col2, ..., value{len(columns)}_for_col{len(columns)}],
      ...
    ]
    
    IMPORTANT GUIDELINES:
    1. COUNT THE VALUES IN EACH ROW. Every row MUST have EXACTLY {len(columns)} values.
    2. Generate REALISTIC values that match the column descriptions and constraints
    3. For dates, use YYYY-MM-DD format (e.g., 2025-05-28)
    4. For timestamps, use YYYY-MM-DD HH:MM:SS format (e.g., 2025-05-28 14:30:00)
    5. For numeric columns, provide appropriate numeric values (not strings)
    6. For text columns, generate meaningful text based on the column name and description
    7. Ensure data is consistent across rows (e.g., related columns should have related values)
    8. DO NOT include any explanations or markdown formatting - ONLY the JSON array
    9. VERIFY that each row has EXACTLY {len(columns)} elements before returning
    10. DO NOT add extra columns that aren't in the list above
    11. DOUBLE CHECK your output before returning - count the number of elements in each row
    12. ENSURE your output is valid JSON - no trailing commas, properly quoted strings, etc.
    13. RETURN ONLY the JSON array of arrays - no explanations, no markdown formatting
    
    Example of a correct response format for a table with 3 columns:
    [["value1", 123, true], ["value2", 456, false], ["value3", 789, true]]
    
    CRITICAL: I will count the number of elements in each row. If any row doesn't have exactly {len(columns)} elements, your response will be rejected.
    """
    
    # Call the LLM with a strong instruction to return only JSON
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "You are a data generation system that ONLY outputs valid JSON arrays. Your ONLY task is to generate sample data with EXACTLY the requested number of columns. Count each row to ensure it has the exact number of columns specified. Do not include any explanations, just the JSON array. CRITICAL: Each row MUST have exactly the same number of elements as there are columns in the table schema."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5  # Lower temperature for more consistent results
    )
    
    # Get the response content
    content = response.choices[0].message.content.strip()
    print(f"Raw LLM response for {table_name}: {content[:100]}...")
    
    # Clean the YAML response from the LLM to ensure it's properly formatted.
    # This function only removes code block markers and trims whitespace.
    # It does not attempt to fix YAML formatting issues - we rely on strict prompting instead.
    def clean_yaml_response(content):
        if not content:
            return content
        
        # Remove markdown code block markers if present
        if '```' in content:
            # Extract content between code block markers
            pattern = r'```(?:yaml)?\s*([\s\S]*?)```'
            matches = re.findall(pattern, content)
            if matches:
                content = matches[0].strip()
            else:
                # If no matches found with the pattern, just remove all ``` markers
                content = re.sub(r'```(?:yaml)?', '', content)
                content = content.replace('```', '').strip()
        
        # Print the cleaned content for debugging
        print(f"\n[DEBUG] Cleaned YAML response:\n{content}")
        
        return content

    content = clean_yaml_response(content)
    
    # Ensure the content is a valid JSON array
    if not (content.startswith('[') and content.endswith(']')):
        # If not a complete JSON array, try to extract it
        json_match = re.search(r'(\[\s*\[.*?\]\s*\])', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            # Try another pattern that might capture the JSON array
            json_match = re.search(r'(\[\s*\[.*)', content, re.DOTALL)
            if json_match:
                # Try to balance the brackets
                partial_content = json_match.group(1)
                open_brackets = partial_content.count('[')
                close_brackets = partial_content.count(']')
                # Add missing closing brackets if needed
                if open_brackets > close_brackets:
                    partial_content += ']' * (open_brackets - close_brackets)
                    content = partial_content
                else:
                    raise ValueError(f"LLM response is not a valid JSON array: {content[:100]}...")
            else:
                raise ValueError(f"LLM response is not a valid JSON array: {content[:100]}...")
    
    try:
        # Parse the JSON
        sample_data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        print(f"Problematic content: {content[:200]}...")
        raise ValueError(f"Failed to parse JSON: {str(e)}")
    
    # Validate the sample data structure
    if not isinstance(sample_data, list):
        raise ValueError(f"Response is not a list. Got {type(sample_data).__name__} instead.")
    
    if len(sample_data) == 0:
        raise ValueError("Sample data is empty. No rows were generated.")
    
    # Check if all rows are lists
    non_list_rows = [i for i, row in enumerate(sample_data) if not isinstance(row, list)]
    if non_list_rows:
        raise ValueError(f"Rows at indices {non_list_rows} are not lists. Got {[type(sample_data[i]).__name__ for i in non_list_rows]}")
    
    # Check if all rows have the correct number of columns
    wrong_length_rows = [i for i, row in enumerate(sample_data) if len(row) != len(columns)]
    if wrong_length_rows:
        print(f"Warning: Rows at indices {wrong_length_rows} don't have {len(columns)} columns. Got {[len(sample_data[i]) for i in wrong_length_rows]}")
        print("Fixing row lengths...")
        
        # Fix the rows with wrong lengths
        for i in wrong_length_rows:
            row = sample_data[i]
            if len(row) > len(columns):
                # Truncate extra columns
                print(f"Truncating row {i} from {len(row)} to {len(columns)} columns")
                sample_data[i] = row[:len(columns)]
            elif len(row) < len(columns):
                # Pad with null values for missing columns
                print(f"Row {i} is too short ({len(row)} columns). This is a critical error.")
                raise ValueError(f"Row {i} has too few columns: {len(row)} instead of {len(columns)}")
    
    # Final validation
    if not all(len(row) == len(columns) for row in sample_data):
        # This should never happen after fixing
        raise ValueError(f"Failed to fix all rows to have exactly {len(columns)} columns")
    
    print(f"Successfully validated sample data: {len(sample_data)} rows, each with {len(columns)} columns")
    
    # Return the valid sample data
    return sample_data

# No more fallback functions - we only use LLM for data generation

if __name__ == '__main__':
    app.run(debug=True)
