import os
import re
import json
import yaml
import time
import datetime
from openai import OpenAI
import numpy as np

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Custom JSON encoder to handle numpy types
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super(NpEncoder, self).default(obj)

def clean_yaml_response(content):
    """
    Clean up YAML content by removing code block markers if present.
    Also handles other common formatting issues in LLM responses.
    """
    if not content:
        return ""
    
    # Remove code block markers if present
    content = re.sub(r'^```yaml\s*', '', content)
    content = re.sub(r'^```yml\s*', '', content)
    content = re.sub(r'^```\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    
    # Handle cases where the LLM adds explanatory text before or after the YAML
    yaml_match = re.search(r'((?:[\w\s]+:[\s\S]*?(?:\n\w+:|\Z))+)', content)
    if yaml_match:
        potential_yaml = yaml_match.group(1)
        try:
            # Verify it's valid YAML
            yaml.safe_load(potential_yaml)
            content = potential_yaml
        except Exception:
            # If not valid YAML, keep original content
            pass
    
    # Handle edge case where LLM adds quotes around the YAML
    if content.startswith('"') and content.endswith('"'):
        content = content[1:-1]
    
    # Handle edge case where LLM escapes quotes
    content = content.replace('\\"', '"')
    
    # Handle edge case where LLM adds indentation to the entire YAML block
    lines = content.split('\n')
    if all(line.startswith('  ') or not line.strip() for line in lines if line.strip()):
        content = '\n'.join(line[2:] if line.startswith('  ') else line for line in lines)
    
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
        return ""
    
    # Remove SQL comments
    sql_query = re.sub(r'--.*?$', '', sql_query, flags=re.MULTILINE)
    sql_query = re.sub(r'/\*[\s\S]*?\*/', '', sql_query)
    
    # Normalize whitespace
    sql_query = re.sub(r'\s+', ' ', sql_query).strip()
    
    # Handle CTEs properly (ensure WITH clause is at the beginning)
    if re.search(r'\bWITH\b', sql_query, re.IGNORECASE) and not sql_query.upper().startswith('WITH '):
        # Extract the WITH clause and move it to the beginning
        with_match = re.search(r'\bWITH\b\s+(.*?)(?:\bSELECT\b)', sql_query, re.IGNORECASE | re.DOTALL)
        if with_match:
            with_clause = with_match.group(0)[:-6]  # Remove the trailing SELECT
            remaining_query = sql_query.replace(with_clause, '')
            sql_query = with_clause + remaining_query
    
    # Ensure semicolon at the end
    if not sql_query.rstrip().endswith(';'):
        sql_query = sql_query.rstrip() + ';'
    
    return sql_query

# Global event tracking
global_events = []
current_file_id = None
current_workflow_state = 'IDLE'

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
    
    # Add to global events list (keep last 50 events)
    global_events.append(event_data)
    if len(global_events) > 50:
        global_events = global_events[-50:]
    
    return event_data
