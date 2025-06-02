import os
import yaml
import json
import sqlite3
import pandas as pd
import uuid
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from openai import OpenAI
from utils import clean_yaml_response, agent_activity, clean_sql_query

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class BaseAgent:
    """Base class for all agents in the NL2SQL system."""
    
    def __init__(self, name):
        self.name = name
        self.model = "gpt-4.1-nano"
        self.temperature = 0.1
    
    def _call_llm(self, system_prompt, user_message, max_tokens=1500):
        """Call the LLM with the given prompts."""
        try:
            agent_activity(self.name, 'PROCESSING', f'Processing with {self.model}')
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            
            content = clean_yaml_response(response.choices[0].message.content)
            return content
            
        except Exception as e:
            agent_activity(self.name, 'ERROR', f'Error calling LLM: {str(e)}')
            return None
    
    def _parse_yaml_response(self, content, default_result=None):
        """Parse YAML response from LLM."""
        if not content:
            return default_result or {}
            
        try:
            result = yaml.safe_load(content)
            return result
        except Exception as e:
            agent_activity(self.name, 'ERROR', f'Error parsing YAML: {str(e)}')
            return default_result or {}
    
    def process(self, *args, **kwargs):
        """Process method to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process method")


class FileClassifierAgent(BaseAgent):
    """Identifies file type and structure."""
    
    def __init__(self):
        super().__init__("FileClassifierAgent")
    
    def process(self, file_path):
        """Analyze the file to determine its type and structure."""
        agent_activity(self.name, 'CLASSIFIED', 'Analyzing file structure')
        
        system_prompt = """
        You are a file classification agent for a natural language to SQL system.
        Your job is to analyze a file and determine:
        1. The file type (CSV, JSON, XML, YAML, Excel, SQL, etc.)
        2. Whether it contains schema definitions or actual data
        3. The structure of the file (tables, columns, relationships)
        
        Respond with a YAML structure containing:
        - file_type: The detected file type
        - content_type: 'schema' or 'data'
        - tables: List of tables detected in the file
        - structure: Description of the file structure
        - recommended_processing: How the file should be processed
        """
        
        # Read the first part of the file for analysis
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read(10000)  # Read first 10KB
        except Exception:
            # Try binary mode if text mode fails
            try:
                with open(file_path, 'rb') as f:
                    file_content = f.read(10000).decode('utf-8', errors='ignore')
            except Exception as e:
                agent_activity(self.name, 'ERROR', f'Error reading file: {str(e)}')
                return {
                    'file_type': 'unknown',
                    'content_type': 'unknown',
                    'tables': [],
                    'structure': 'Could not read file',
                    'recommended_processing': 'manual'
                }
        
        # Create user message with file info and content
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        user_message = f"""File name: {file_name}
File extension: {file_ext}
File size: {file_size} bytes

File content preview:
{file_content}"""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message)
        result = self._parse_yaml_response(content, {
            'file_type': file_ext.replace('.', '') or 'unknown',
            'content_type': 'data',
            'tables': [],
            'structure': 'Unknown structure',
            'recommended_processing': 'standard'
        })
        
        agent_activity(self.name, 'COMPLETED', 'File classification completed', 
                      {'file_type': result.get('file_type', 'unknown')})
        
        return result


class DataProfilerAgent(BaseAgent):
    """Analyzes data patterns, types, and statistics."""
    
    def __init__(self):
        super().__init__("DataProfilerAgent")
    
    def process(self, file_path, classification_result):
        """Profile the data in the file."""
        agent_activity(self.name, 'PROFILED', 'Profiling data')
        
        system_prompt = """
        You are a data profiling agent for a natural language to SQL system.
        Your job is to analyze data and determine:
        1. Column data types and patterns
        2. Data quality issues
        3. Statistical properties (min, max, avg, etc.)
        4. Potential primary and foreign keys
        
        Respond with a YAML structure containing:
        - tables: Dictionary of table profiles, each containing:
          - columns: Dictionary of column profiles
          - row_count: Estimated number of rows
          - quality_issues: Any detected quality issues
          - recommended_indexes: Columns that should be indexed
        """
        
        # Create user message with file info and classification
        user_message = f"""File path: {file_path}
Classification results:
{yaml.dump(classification_result)}

Please profile the data in this file."""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message, max_tokens=2000)
        result = self._parse_yaml_response(content, {
            'tables': {},
            'quality_issues': [],
            'recommended_indexes': []
        })
        
        agent_activity(self.name, 'COMPLETED', 'Data profiling completed',
                      {'table_count': len(result.get('tables', {}))})
        
        return result


class DictionarySynthesizerAgent(BaseAgent):
    """Creates schema/dictionary from profiled data."""
    
    def __init__(self):
        super().__init__("DictionarySynthesizerAgent")
    
    def process(self, profile_result, classification_result):
        """Create a data dictionary from the profiling results."""
        agent_activity(self.name, 'DICT_DRAFT', 'Creating data dictionary')
        
        system_prompt = """
        You are a dictionary synthesis agent for a natural language to SQL system.
        Your job is to create a comprehensive data dictionary by:
        1. Defining each table and its purpose
        2. Describing each column, its data type, and meaning
        3. Identifying relationships between tables
        4. Suggesting query patterns for common questions
        
        Respond with a YAML structure containing:
        - tables: Dictionary of table definitions
        - columns: Dictionary of column definitions
        - relationships: List of table relationships
        - common_queries: Examples of common queries
        """
        
        # Create user message with profiling and classification results
        user_message = f"""Classification results:
{yaml.dump(classification_result)}

Profiling results:
{yaml.dump(profile_result)}

Please create a comprehensive data dictionary."""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message, max_tokens=2500)
        result = self._parse_yaml_response(content, {
            'tables': {},
            'columns': {},
            'relationships': [],
            'common_queries': []
        })
        
        agent_activity(self.name, 'COMPLETED', 'Data dictionary created',
                      {'table_count': len(result.get('tables', {}))})
        
        return result


class ConversationalAgent(BaseAgent):
    """Manages multi-turn conversations and query clarification."""
    
    def __init__(self):
        super().__init__("ConversationalAgent")
    
    def process(self, query, conversation_history=None):
        """Process the query in the context of the conversation history."""
        agent_activity(self.name, 'PROCESSING', 'Processing conversational context')
        
        # Initialize conversation history if not provided
        if conversation_history is None:
            conversation_history = []
        
        system_prompt = """
        You are a conversational agent for a natural language to SQL system. 
        Your job is to:
        1. Understand the user's query in the context of the conversation history
        2. Determine if the query is clear and complete
        3. If the query is ambiguous or incomplete, generate follow-up questions
        4. If the query is clear, normalize it for further processing
        
        Respond with a YAML structure containing:
        - normalized_query: The clarified query ready for processing
        - needs_clarification: true/false
        - follow_up_questions: List of questions if clarification is needed
        - conversation_context: Key information to remember for future queries
        """
        
        # Format conversation history for the prompt
        conversation_text = "\n".join([f"Turn {i+1}:\nUser: {turn['query']}\nSystem: {turn.get('response', '')}" 
                                    for i, turn in enumerate(conversation_history)])
        
        # Create the user message
        user_message = f"""Current query: {query}

Conversation history:
{conversation_text}"""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message)
        result = self._parse_yaml_response(content, {
            'normalized_query': query,
            'needs_clarification': False,
            'follow_up_questions': [],
            'conversation_context': {}
        })
        
        agent_activity(self.name, 'COMPLETED', 'Processed conversational context',
                      {'needs_clarification': result.get('needs_clarification', False)})
        
        return result


class QueryNormalizerAgent(BaseAgent):
    """Standardizes and cleans queries."""
    
    def __init__(self):
        super().__init__("QueryNormalizerAgent")
    
    def process(self, query, table_info):
        """Normalize the query for further processing."""
        agent_activity(self.name, 'PROCESSING', 'Normalizing query')
        
        system_prompt = """
        You are a query normalization agent for a natural language to SQL system.
        Your job is to standardize and clean the user's query by:
        1. Resolving ambiguities in natural language
        2. Expanding abbreviations and domain-specific terms
        3. Ensuring the query is clear and precise
        4. Identifying the tables and columns referenced in the query
        
        Respond with a YAML structure containing:
        - normalized_query: The standardized query
        - referenced_tables: List of tables mentioned or implied in the query
        - referenced_columns: List of columns mentioned or implied in the query
        - query_type: The type of query (SELECT, INSERT, UPDATE, DELETE, etc.)
        - aggregation_functions: Any aggregation functions detected (COUNT, SUM, AVG, etc.)
        """
        
        # Format table info for the prompt
        table_info_text = "\n".join([f"Table: {table}\nColumns: {', '.join(columns)}" 
                                   for table, columns in table_info.items()])
        
        # Create the user message
        user_message = f"""Query: {query}

Available tables and columns:
{table_info_text}"""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message)
        result = self._parse_yaml_response(content, {
            'normalized_query': query,
            'referenced_tables': [],
            'referenced_columns': [],
            'query_type': 'SELECT',
            'aggregation_functions': []
        })
        
        agent_activity(self.name, 'COMPLETED', 'Query normalized',
                      {'normalized_query': result.get('normalized_query', query)})
        
        return result


class QueryDecomposerAgent(BaseAgent):
    """Breaks down complex queries into sub-queries."""
    
    def __init__(self):
        super().__init__("QueryDecomposerAgent")
    
    def process(self, normalized_query, query_info, table_info):
        """Decompose the query into sub-queries if needed."""
        agent_activity(self.name, 'PROCESSING', 'Decomposing query')
        
        system_prompt = """
        You are a query decomposition agent for a natural language to SQL system.
        Your job is to break down complex queries into simpler sub-queries by:
        1. Identifying independent parts of the query that can be executed separately
        2. Determining dependencies between sub-queries
        3. Creating a logical execution order
        
        Respond with a YAML structure containing:
        - needs_decomposition: true/false whether the query needs to be broken down
        - sub_queries: List of sub-query objects, each containing:
          - id: Unique identifier for the sub-query
          - query: The natural language sub-query
          - depends_on: List of sub-query IDs this query depends on
          - description: Brief description of what this sub-query does
        - execution_order: List of sub-query IDs in the order they should be executed
        """
        
        # Format table info for the prompt
        table_info_text = "\n".join([f"Table: {table}\nColumns: {', '.join(columns)}" 
                                   for table, columns in table_info.items()])
        
        # Create the user message
        user_message = f"""Normalized query: {normalized_query}

Query information:
{yaml.dump(query_info)}

Available tables and columns:
{table_info_text}"""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message, max_tokens=1500)
        result = self._parse_yaml_response(content, {
            'needs_decomposition': False,
            'sub_queries': [{
                'id': 'main',
                'query': normalized_query,
                'depends_on': [],
                'description': 'Original query'
            }],
            'execution_order': ['main']
        })
        
        agent_activity(self.name, 'COMPLETED', 'Query decomposed',
                      {'needs_decomposition': result.get('needs_decomposition', False)})
        
        return result


class ExecutionPlannerAgent(BaseAgent):
    """Creates execution plans for hybrid SQL/Python processing."""
    
    def __init__(self):
        super().__init__("ExecutionPlannerAgent")
    
    def process(self, decomposed_query, table_info):
        """Create an execution plan for the query or sub-queries."""
        agent_activity(self.name, 'PROCESSING', 'Creating execution plan')
        
        system_prompt = """
        You are an execution planning agent for a natural language to SQL/Python system.
        Your job is to create an optimal execution plan by:
        1. Determining whether each query/sub-query is best executed using SQL or Python
        2. Creating a directed acyclic graph (DAG) of execution steps
        3. Identifying dependencies between steps
        
        For each query or sub-query, decide whether it should be executed using:
        - SQL: For straightforward data retrieval/manipulation tasks
        - Python: For complex calculations, custom aggregations, or visualizations
        
        Respond with a YAML structure containing:
        - execution_steps: List of step objects, each containing:
          - id: Unique identifier for the step
          - query_id: ID of the sub-query this step executes
          - execution_type: 'sql' or 'python'
          - description: What this step does
          - depends_on: List of step IDs this step depends on
          - expected_output: Description of the expected output
        - execution_order: List of step IDs in the order they should be executed
        - final_result_step: ID of the step that produces the final result
        """
        
        # Format table info for the prompt
        table_info_text = "\n".join([f"Table: {table}\nColumns: {', '.join(columns)}" 
                                   for table, columns in table_info.items()])
        
        # Create the user message
        user_message = f"""Decomposed query:
{yaml.dump(decomposed_query)}

Available tables and columns:
{table_info_text}"""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message, max_tokens=2000)
        result = self._parse_yaml_response(content)
        
        agent_activity(self.name, 'COMPLETED', 'Execution plan created',
                      {'step_count': len(result.get('execution_steps', []))})
        
        return result


class SQLGeneratorAgent(BaseAgent):
    """Translates natural language to SQL."""
    
    def __init__(self):
        super().__init__("SQLGeneratorAgent")
    
    def process(self, query, table_info, data_dict=None):
        """Convert a natural language query to SQL."""
        agent_activity(self.name, 'PROCESSING', 'Generating SQL query')
        
        system_prompt = """
        You are a SQL generation agent for a natural language to SQL system.
        Your job is to convert natural language queries to SQL by:
        1. Analyzing the query intent
        2. Identifying the required tables and columns
        3. Creating appropriate joins, filters, and aggregations
        4. Ensuring the SQL is valid for SQLite
        
        Respond with a YAML structure containing:
        - sql: The generated SQL query
        - tables_used: List of tables used in the query
        - columns_used: List of columns used in the query
        - reasoning: Explanation of how you translated the query
        - confidence: Your confidence in the translation (0-100)
        """
        
        # Format table info for the prompt
        table_info_text = "\n".join([f"Table: {table}\nColumns: {', '.join(columns)}" 
                                   for table, columns in table_info.items()])
        
        # Add data dictionary if available
        data_dict_text = ""
        if data_dict:
            data_dict_text = f"\n\nData Dictionary:\n{yaml.dump(data_dict)}"
        
        # Create the user message
        user_message = f"""Query: {query}

Available tables and columns:
{table_info_text}{data_dict_text}"""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message, max_tokens=2000)
        result = self._parse_yaml_response(content)
        
        # Clean the SQL query
        result['sql'] = clean_sql_query(result.get('sql', ''))
        
        agent_activity(self.name, 'COMPLETED', 'SQL query generated',
                      {'confidence': result.get('confidence', 0)})
        
        return result


class SQLExecutorAgent(BaseAgent):
    """Executes SQL queries against the database."""
    
    def __init__(self):
        super().__init__("SQLExecutorAgent")
    
    def process(self, sql_query, db_path):
        """Execute the SQL query and return the results."""
        agent_activity(self.name, 'PROCESSING', 'Executing SQL query')
        
        try:
            # Connect to the database
            conn = sqlite3.connect(db_path)
            
            # Execute the query
            df = pd.read_sql_query(sql_query, conn)
            
            # Close the connection
            conn.close()
            
            # Convert to records for JSON serialization
            records = df.to_dict(orient='records')
            columns = df.columns.tolist()
            
            agent_activity(self.name, 'COMPLETED', 'SQL query executed',
                          {'row_count': len(records), 'column_count': len(columns)})
            
            return {
                'success': True,
                'records': records,
                'columns': columns,
                'row_count': len(records),
                'column_count': len(columns)
            }
            
        except Exception as e:
            error_message = str(e)
            agent_activity(self.name, 'ERROR', f'Error executing SQL: {error_message}')
            
            return {
                'success': False,
                'error': error_message,
                'records': [],
                'columns': [],
                'row_count': 0,
                'column_count': 0
            }


class CodeGeneratorAgent(BaseAgent):
    """Generates Python code for complex operations."""
    
    def __init__(self):
        super().__init__("CodeGeneratorAgent")
    
    def process(self, step, sub_query, table_info, db_path):
        """Generate Python code for the given execution step."""
        agent_activity(self.name, 'PROCESSING', f'Generating code for step {step["id"]}')
        
        system_prompt = """
        You are a Python code generation agent for a natural language to SQL/Python system.
        Your job is to generate Python code that:
        1. Connects to the SQLite database
        2. Performs the required data processing or visualization
        3. Returns the results in a structured format
        
        Use pandas, matplotlib, or other libraries as needed.
        The code should be self-contained and ready to execute.
        
        Respond with a YAML structure containing:
        - code: The complete Python code to execute
        - description: Brief description of what the code does
        - expected_output_type: The type of output (dataframe, plot, scalar, etc.)
        - libraries_used: List of libraries used in the code
        """
        
        # Format table info for the prompt
        table_info_text = "\n".join([f"Table: {table}\nColumns: {', '.join(columns)}" 
                                   for table, columns in table_info.items()])
        
        # Create the user message
        user_message = f"""Execution step:
{yaml.dump(step)}

Sub-query: {sub_query}

Available tables and columns:
{table_info_text}

SQLite database path: {db_path}"""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message, max_tokens=2500)
        result = self._parse_yaml_response(content)
        
        agent_activity(self.name, 'COMPLETED', f'Code generated for step {step["id"]}',
                      {'libraries_used': result.get('libraries_used', [])})
        
        return result


class CodeExecutorAgent(BaseAgent):
    """Executes Python code in a sandboxed environment."""
    
    def __init__(self):
        super().__init__("CodeExecutorAgent")
    
    def process(self, code_info):
        """Execute the generated Python code and return the results."""
        agent_activity(self.name, 'PROCESSING', 'Executing Python code')
        
        # Extract the code to execute
        code = code_info.get('code', '')
        if not code:
            agent_activity(self.name, 'ERROR', 'No code provided for execution')
            return {
                'success': False,
                'error': 'No code provided for execution',
                'result': None
            }
        
        # Create a temporary file for the code
        code_file = os.path.join('temp', f'code_{uuid.uuid4()}.py')
        with open(code_file, 'w') as f:
            f.write(code)
        
        # Prepare a dictionary for local and global variables
        local_vars = {}
        
        try:
            # Execute the code in a controlled environment
            with open(code_file, 'r') as f:
                code_content = f.read()
            
            # Execute the code
            exec(code_content, globals(), local_vars)
            
            # Check for a 'result' variable in the local scope
            if 'result' in local_vars:
                result = local_vars['result']
                
                # Convert pandas DataFrame to dict for JSON serialization
                if 'pandas.core.frame.DataFrame' in str(type(result)):
                    result_data = result.to_dict(orient='records')
                    columns = result.columns.tolist()
                    return {
                        'success': True,
                        'result_type': 'dataframe',
                        'records': result_data,
                        'columns': columns,
                        'row_count': len(result_data),
                        'column_count': len(columns)
                    }
                
                # Handle matplotlib figures
                elif 'matplotlib.figure.Figure' in str(type(result)):
                    # Save the figure to a bytes buffer
                    buf = BytesIO()
                    result.savefig(buf, format='png')
                    buf.seek(0)
                    
                    # Convert to base64 for embedding in HTML
                    img_str = base64.b64encode(buf.read()).decode('utf-8')
                    
                    return {
                        'success': True,
                        'result_type': 'plot',
                        'image_data': img_str,
                        'format': 'png'
                    }
                
                # Handle other types
                else:
                    # Try to convert to a JSON-serializable format
                    try:
                        json.dumps({'result': result})
                        return {
                            'success': True,
                            'result_type': 'scalar',
                            'value': result
                        }
                    except (TypeError, OverflowError):
                        return {
                            'success': True,
                            'result_type': 'text',
                            'value': str(result)
                        }
            else:
                agent_activity(self.name, 'WARNING', 'No result variable found in executed code')
                return {
                    'success': True,
                    'result_type': 'none',
                    'message': 'Code executed successfully but no result was returned'
                }
                
        except Exception as e:
            error_message = str(e)
            agent_activity(self.name, 'ERROR', f'Error executing code: {error_message}')
            
            return {
                'success': False,
                'error': error_message,
                'result': None
            }
        finally:
            # Clean up the temporary file
            try:
                os.remove(code_file)
            except:
                pass


class SQLGeneratorAgent(BaseAgent):
    """Generates SQL queries from natural language."""
    
    def __init__(self):
        super().__init__("SQLGeneratorAgent")
    
    def process(self, query, table_info, data_dict=None):
        """Generate SQL from natural language query."""
        agent_activity(self.name, 'PROCESSING', 'Generating SQL query')
        
        system_prompt = """
        You are a SQL generation agent for a natural language to SQL system.
        Your job is to convert natural language queries into correct SQL queries by:
        1. Analyzing the query intent and required data
        2. Identifying the relevant tables and columns
        3. Creating a SQL query that will correctly retrieve the requested information
        
        Follow these rules:
        - Use only tables and columns that exist in the provided schema
        - Use appropriate joins when multiple tables are involved
        - Add comments to explain complex parts of the query
        - Handle aggregations, grouping, and sorting as needed
        - Use CTEs for complex queries to improve readability
        
        Respond with a YAML structure containing:
        - sql: The generated SQL query
        - explanation: Brief explanation of how the SQL works
        - tables_used: List of tables used in the query
        - confidence: Your confidence level (high, medium, low)
        """
        
        # Format table info for the prompt
        tables_str = ""
        for table, columns in table_info.items():
            tables_str += f"Table: {table}\nColumns: {', '.join(columns)}\n\n"
        
        # Add data dictionary if available
        data_dict_str = ""
        if data_dict:
            data_dict_str = "\nData Dictionary:\n" + json.dumps(data_dict, indent=2)
        
        # Create the user message
        user_message = f"""Query: {query}

Available Schema:
{tables_str}{data_dict_str}

Generate a SQL query to answer this question."""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message)
        result = self._parse_yaml_response(content)
        
        # Clean the SQL query
        if 'sql' in result and result['sql']:
            result['sql'] = clean_sql_query(result['sql'])
        
        agent_activity(self.name, 'COMPLETED', 'SQL query generated', 
                      {'tables_used': result.get('tables_used', []), 
                       'confidence': result.get('confidence', 'low')})
        
        return result


class SQLExecutorAgent(BaseAgent):
    """Executes SQL queries against a database."""
    
    def __init__(self):
        super().__init__("SQLExecutorAgent")
    
    def process(self, sql_query, db_path):
        """Execute SQL query and return results."""
        if not sql_query or not sql_query.strip():
            agent_activity(self.name, 'ERROR', 'Empty SQL query')
            return {
                'success': False,
                'error': 'Empty SQL query',
                'result': None
            }
        
        agent_activity(self.name, 'PROCESSING', 'Executing SQL query')
        
        try:
            # Connect to the database
            conn = sqlite3.connect(db_path)
            
            # Execute the query
            df = pd.read_sql_query(sql_query, conn)
            
            # Close the connection
            conn.close()
            
            # Convert DataFrame to dict for JSON serialization
            result = {
                'success': True,
                'result_type': 'dataframe',
                'dataframe': df.to_dict(orient='records'),
                'columns': df.columns.tolist(),
                'row_count': len(df)
            }
            
            agent_activity(self.name, 'COMPLETED', 'SQL query executed successfully', 
                          {'row_count': len(df), 'column_count': len(df.columns)})
            
            return result
            
        except Exception as e:
            error_message = str(e)
            agent_activity(self.name, 'ERROR', f'Error executing SQL: {error_message}')
            
            return {
                'success': False,
                'error': error_message,
                'result': None
            }


class ResultCombinerAgent(BaseAgent):
    """Joins results from multiple execution paths."""
    
    def __init__(self):
        super().__init__("ResultCombinerAgent")
    
    def process(self, execution_results, execution_plan, original_query):
        """Combine results from multiple execution steps."""
        agent_activity(self.name, 'PROCESSING', 'Combining execution results')
        
        # If there's only one result, return it directly
        if len(execution_results) == 1:
            step_id = list(execution_results.keys())[0]
            result = execution_results[step_id]
            
            agent_activity(self.name, 'COMPLETED', 'Single result returned directly')
            return {
                'success': result.get('success', False),
                'combined_type': result.get('result_type', 'unknown'),
                'result': result,
                'summary': f"Result from step {step_id}"
            }
        
        # For multiple results, ask the LLM how to combine them
        system_prompt = """
        You are a result combination agent for a natural language to SQL/Python system.
        Your job is to combine results from multiple execution steps by:
        1. Analyzing the type and content of each result
        2. Determining the best way to combine or present them
        3. Creating a natural language summary of the combined results
        
        Respond with a YAML structure containing:
        - combination_strategy: How the results should be combined
        - primary_result_id: The ID of the most important result
        - presentation_order: List of result IDs in the order they should be presented
        - summary: Natural language summary of the combined results
        """
        
        # Create the user message
        user_message = f"""Original query: {original_query}

Execution plan:
{yaml.dump(execution_plan)}

Execution results:
{yaml.dump({k: {'type': v.get('result_type', 'unknown'), 'success': v.get('success', False)} for k, v in execution_results.items()})}"""
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message)
        combination_plan = self._parse_yaml_response(content)
        
        # Use the combination plan to structure the results
        combined_result = {
            'success': all(r.get('success', False) for r in execution_results.values()),
            'combined_type': 'multi',
            'results': execution_results,
            'combination_strategy': combination_plan.get('combination_strategy'),
            'primary_result_id': combination_plan.get('primary_result_id'),
            'presentation_order': combination_plan.get('presentation_order'),
            'summary': combination_plan.get('summary')
        }
        
        agent_activity(self.name, 'COMPLETED', 'Results combined',
                      {'result_count': len(execution_results)})
        
        return combined_result
