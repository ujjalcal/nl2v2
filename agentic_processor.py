import os
import json
import re
import pandas as pd
import sqlite3
import os
from typing import Dict, List, Any, Optional, Tuple, Union
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debug API key (masked for security)
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    masked_key = api_key[:10] + "..." if len(api_key) > 10 else "None"
    print(f"[AgenticProcessor] API Key loaded (first 10 chars): {masked_key}")
else:
    print("[AgenticProcessor] WARNING: No OpenAI API key found in environment variables")

class AgenticQueryProcessor:
    """
    An agentic query processor that breaks down complex queries,
    creates execution plans, and processes them using appropriate tools.
    """
    
    def __init__(self, data_dict_path: Optional[str] = None, db_path: Optional[str] = None):
        """
        Initialize the AgenticQueryProcessor.
        
        Args:
            data_dict_path: Optional path to a data dictionary JSON file
            db_path: Optional path to a SQLite database file
        """
        # Get API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("WARNING: OpenAI API key not found. NL2SQL functionality will not work.")
        else:
            masked_key = api_key[:10] + "..." if len(api_key) > 10 else "None"
            print(f"[AgenticProcessor.__init__] Using API Key (first 10 chars): {masked_key}")
            
        # Initialize OpenAI client with explicit API key
        self.client = OpenAI(api_key=api_key)
        
        self._data_dict_path = data_dict_path
        self._db_path = db_path
        self.data_dict = self._load_data_dictionary(data_dict_path) if data_dict_path else None
        self.db_conn = None
        self.execution_plan = []
        self.execution_results = []
        self.reasoning_steps = []
        
        # Connect to database if provided
        if self.db_path:
            self._connect_to_db()
    
    @property
    def data_dict_path(self):
        return self._data_dict_path
    
    @data_dict_path.setter
    def data_dict_path(self, path):
        self._data_dict_path = path
        if path:
            self.data_dict = self._load_data_dictionary(path)
    
    @property
    def db_path(self):
        return self._db_path
    
    @db_path.setter
    def db_path(self, path):
        self._db_path = path
        if path:
            # Close existing connection if any
            if self.db_conn:
                try:
                    self.db_conn.close()
                except:
                    pass
            # Connect to the new database
            self._connect_to_db()
    
    def _connect_to_db(self) -> None:
        """Connect to the SQLite database with improved error handling."""
        if not self.db_path:
            print("No database path specified. Please upload a file first.")
            self.db_conn = None
            return
            
        # Check if the database file exists
        if not os.path.exists(self.db_path):
            print(f"Database file not found at path: {self.db_path}")
            self.db_conn = None
            return
            
        try:
            # Use check_same_thread=False to avoid thread safety issues with Streamlit
            self.db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.db_conn.row_factory = sqlite3.Row
            
            # Test the connection by executing a simple query
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Successfully connected to database with {len(tables)} tables")
        except sqlite3.Error as e:
            print(f"SQLite error connecting to database: {str(e)}")
            self.db_conn = None
        except Exception as e:
            print(f"Unexpected error connecting to database: {str(e)}")
            self.db_conn = None
    
    def _load_data_dictionary(self, path: str) -> Dict[str, Any]:
        """Load a data dictionary from a JSON or YAML file."""
        try:
            if not path or not os.path.exists(path):
                print(f"Data dictionary file not found: {path}")
                return {}
                
            file_extension = path.split('.')[-1].lower()
            with open(path, 'r') as f:
                if file_extension in ['yaml', 'yml']:
                    import yaml
                    return yaml.safe_load(f)
                else:  # Default to JSON
                    return json.load(f)
        except Exception as e:
            print(f"Error loading data dictionary: {str(e)}")
            return {}
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query using the agentic approach.
        
        Args:
            query: The natural language query to process
            
        Returns:
            Dictionary containing the results and execution details
        """
        # Reset execution state
        self.execution_plan = []
        self.execution_results = []
        self.reasoning_steps = []
        
        # Add initial reasoning step
        self._add_reasoning_step("Query Analysis", f"Analyzing query: '{query}'")
        
        # Analyze query complexity
        complexity, query_type = self._analyze_query_complexity(query)
        self._add_reasoning_step("Complexity Analysis", f"Query complexity: {complexity}, Type: {query_type}")
        
        # Process based on complexity
        if complexity == "simple":
            return self._process_simple_query(query, query_type)
        else:
            return self._process_complex_query(query)
    
    def _analyze_query_complexity(self, query: str) -> Tuple[str, str]:
        """
        Analyze the complexity and type of a query.
        
        Args:
            query: The query to analyze
            
        Returns:
            Tuple of (complexity, query_type)
            complexity: 'simple' or 'complex'
            query_type: 'sql', 'python', or 'hybrid'
        """
        # Check if query might need joins
        tables = self._get_all_tables()
        might_need_join = self._query_might_need_join(query, tables)
        
        # Create prompt for GPT
        prompt = f"""
        Analyze the following query and determine its complexity and type:
        
        Query: "{query}"
        
        Available tables: {', '.join(tables)}
        {"This query might require joins between tables." if might_need_join else ""}
        
        Classify the query as:
        1. Complexity: 'simple' (can be answered in one step) or 'complex' (requires multiple steps)
        2. Type: 'sql' (can be answered with SQL alone), 'python' (requires Python processing), or 'hybrid' (needs both)
        
        Respond in JSON format with two fields: "complexity" and "type".
        """
        
        # Query GPT
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes query complexity."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=150
        )
        
        # Parse response
        try:
            result = json.loads(response.choices[0].message.content)
            return result.get("complexity", "simple"), result.get("type", "sql")
        except:
            # Default to simple SQL query if parsing fails
            return "simple", "sql"
    
    def _process_simple_query(self, query: str, query_type: str) -> Dict[str, Any]:
        """
        Process a simple query using the appropriate tool.
        
        Args:
            query: The query to process
            query_type: The type of query ('sql', 'python', or 'hybrid')
            
        Returns:
            Dictionary containing the results and execution details
        """
        self._add_reasoning_step("Processing Approach", f"Processing as a simple {query_type} query")
        
        if query_type == "sql":
            # Generate and execute SQL
            sql_query = self._generate_sql_query(query)
            self._add_reasoning_step("SQL Generation", f"Generated SQL: {sql_query}")
            
            # Add to execution plan
            self.execution_plan.append({
                "step": 1,
                "action": "execute_sql",
                "query": sql_query
            })
            
            # Execute SQL
            if self.db_conn:
                try:
                    results = self._execute_sql(sql_query)
                    self._add_reasoning_step("SQL Execution", "SQL executed successfully")
                    self.execution_results.append({
                        "step": 1,
                        "results": results
                    })
                except Exception as e:
                    error_msg = str(e)
                    self._add_reasoning_step("SQL Execution Error", f"Error: {error_msg}")
                    self.execution_results.append({
                        "step": 1,
                        "error": error_msg
                    })
                    results = []
            else:
                self._add_reasoning_step("Database Connection Error", "No database connection available")
                results = []
            
            # Generate summary
            summary = self._generate_summary(query, results)
            
            return {
                "query": query,
                "complexity": "simple",
                "type": query_type,
                "execution_plan": self.execution_plan,
                "execution_results": self.execution_results,
                "reasoning_steps": self.reasoning_steps,
                "summary": summary,
                "results": results
            }
            
        elif query_type == "python":
            # Generate Python code
            python_code = self._generate_python_code(query)
            self._add_reasoning_step("Python Code Generation", f"Generated Python code:\n{python_code}")
            
            # Add to execution plan
            self.execution_plan.append({
                "step": 1,
                "action": "execute_python",
                "code": python_code
            })
            
            # Execute Python (in a safe, controlled manner)
            try:
                results = self._execute_python(python_code)
                self._add_reasoning_step("Python Execution", "Python code executed successfully")
                self.execution_results.append({
                    "step": 1,
                    "results": results
                })
            except Exception as e:
                error_msg = str(e)
                self._add_reasoning_step("Python Execution Error", f"Error: {error_msg}")
                self.execution_results.append({
                    "step": 1,
                    "error": error_msg
                })
                results = []
            
            # Generate summary
            summary = self._generate_summary(query, results)
            
            return {
                "query": query,
                "complexity": "simple",
                "type": query_type,
                "execution_plan": self.execution_plan,
                "execution_results": self.execution_results,
                "reasoning_steps": self.reasoning_steps,
                "summary": summary,
                "results": results
            }
            
        else:  # hybrid
            self._add_reasoning_step("Query Reclassification", "Hybrid query detected, treating as complex")
            return self._process_complex_query(query)
    
    def _process_complex_query(self, query: str) -> Dict[str, Any]:
        """
        Process a complex query by breaking it down into subtasks.
        
        Args:
            query: The complex query to process
            
        Returns:
            Dictionary containing the results and execution details
        """
        self._add_reasoning_step("Processing Approach", "Processing as a complex query")
        
        # Generate subtasks
        subtasks = self._generate_subtasks(query)
        self._add_reasoning_step("Subtask Generation", f"Generated {len(subtasks)} subtasks")
        
        # Create execution plan
        self._create_execution_plan(subtasks)
        self._add_reasoning_step("Execution Planning", f"Created execution plan with {len(self.execution_plan)} steps")
        
        # Execute plan
        all_results = []
        for step in self.execution_plan:
            step_num = step["step"]
            action = step["action"]
            
            self._add_reasoning_step(f"Executing Step {step_num}", f"Action: {action}")
            
            if action == "execute_sql":
                sql_query = step["query"]
                try:
                    if self.db_conn:
                        results = self._execute_sql(sql_query)
                        self._add_reasoning_step(f"Step {step_num} SQL Execution", "SQL executed successfully")
                        self.execution_results.append({
                            "step": step_num,
                            "results": results
                        })
                        all_results.append(results)
                    else:
                        self._add_reasoning_step(f"Step {step_num} Database Error", "No database connection available")
                        self.execution_results.append({
                            "step": step_num,
                            "error": "No database connection available"
                        })
                except Exception as e:
                    error_msg = str(e)
                    self._add_reasoning_step(f"Step {step_num} SQL Error", f"Error: {error_msg}")
                    self.execution_results.append({
                        "step": step_num,
                        "error": error_msg
                    })
            
            elif action == "execute_python":
                python_code = step["code"]
                try:
                    results = self._execute_python(python_code)
                    self._add_reasoning_step(f"Step {step_num} Python Execution", "Python code executed successfully")
                    self.execution_results.append({
                        "step": step_num,
                        "results": results
                    })
                    all_results.append(results)
                except Exception as e:
                    error_msg = str(e)
                    self._add_reasoning_step(f"Step {step_num} Python Error", f"Error: {error_msg}")
                    self.execution_results.append({
                        "step": step_num,
                        "error": error_msg
                    })
        
        # Consolidate results
        consolidated_results = self._consolidate_results(all_results)
        self._add_reasoning_step("Result Consolidation", "Consolidated results from all steps")
        
        # Generate summary
        summary = self._generate_summary(query, consolidated_results)
        
        return {
            "query": query,
            "complexity": "complex",
            "execution_plan": self.execution_plan,
            "execution_results": self.execution_results,
            "reasoning_steps": self.reasoning_steps,
            "summary": summary,
            "results": consolidated_results
        }
    
    def _analyze_join_requirements(self, query: str, tables: List[str], table_schemas: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        Use OpenAI to analyze if a query requires joins and which tables are relevant.
        
        Args:
            query: The natural language query
            tables: List of available tables
            table_schemas: Dictionary mapping table names to their schemas
            
        Returns:
            Dictionary with join analysis information
        """
        if len(tables) <= 1:
            # No need for join analysis with only one table
            return None
        
        # Create a concise schema representation for the prompt
        schema_text = []
        for table in tables:
            columns = list(table_schemas[table].keys())
            schema_text.append(f"Table: {table}\nColumns: {', '.join(columns)}")
        
        # Create prompt for GPT
        prompt = f"""
        Analyze this natural language query and determine which tables and joins are needed to answer it.
        
        Query: "{query}"
        
        Database Schema:
        {"\n\n".join(schema_text)}
        
        Please provide the following information in JSON format:
        1. relevant_tables: List of table names that are needed to answer this query
        2. join_recommendations: List of recommended join conditions (e.g., "Join customers and orders on customer_id")
        3. query_guidance: Specific guidance for constructing the SQL query
        4. summary: A brief summary of your join analysis
        5. requires_join: Boolean indicating if this query requires joins between tables
        
        Only include tables that are directly relevant to answering the query.
        """
        
        # Query GPT
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
                messages=[
                    {"role": "system", "content": "You are an expert database analyst specializing in SQL join analysis. You determine which tables and joins are needed to answer natural language queries."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            # Parse the response
            analysis = json.loads(response.choices[0].message.content)
            
            # Add reasoning step
            self._add_reasoning_step(
                "Join Analysis",
                f"Query: '{query}'\n" +
                f"Relevant tables: {', '.join(analysis.get('relevant_tables', []))}\n" +
                f"Requires join: {analysis.get('requires_join', False)}\n" +
                f"Summary: {analysis.get('summary', 'No summary provided.')}"
            )
            
            return analysis
        except Exception as e:
            # Log the error but continue with query generation
            print(f"Error in join analysis: {str(e)}")
            self._add_reasoning_step(
                "Join Analysis Error",
                f"Failed to analyze join requirements: {str(e)}"
            )
            return None

    def _generate_sql_query(self, query: str) -> str:
        """
        Generate a SQL query from a natural language query.
        
        Args:
            query: The natural language query
            
        Returns:
            SQL query string
        """
        # Get all tables from database
        tables = self._get_all_tables()
        
        # Get schema for each table
        table_schemas = {}
        for table in tables:
            table_schemas[table] = self._get_table_schema(table)
        
        # First, use OpenAI to analyze if the query needs joins and which tables are relevant
        join_analysis = self._analyze_join_requirements(query, tables, table_schemas)
        
        # Prepare context from data dictionary if available
        context = ""
        if self.data_dict:
            fields_info = []
            for field in self.data_dict:
                if field not in ["dataset_name", "description", "fields_count"]:
                    field_data = self.data_dict[field]
                    fields_info.append(f"Field: {field}")
                    fields_info.append(f"  Type: {field_data.get('type', 'unknown')}")
                    fields_info.append(f"  Description: {field_data.get('description', 'No description')}")
                    if field_data.get('relationships'):
                        fields_info.append(f"  Related to: {', '.join(field_data['relationships'])}")
            
            if fields_info:
                context = "Data Dictionary Information:\n" + "\n".join(fields_info)
    
        # Add database schema information, prioritizing relevant tables first
        schema_info = []
        
        # Add relevant tables first if we have join analysis
        if join_analysis and join_analysis.get("relevant_tables"):
            relevant_tables = join_analysis["relevant_tables"]
            for table in relevant_tables:
                if table in table_schemas:
                    schema_info.append(f"Table: {table} (RELEVANT)")
                    for column, col_type in table_schemas[table].items():
                        schema_info.append(f"  Column: {column}, Type: {col_type}")
            
            # Add remaining tables
            for table in tables:
                if table not in relevant_tables:
                    schema_info.append(f"Table: {table}")
                    for column, col_type in table_schemas[table].items():
                        schema_info.append(f"  Column: {column}, Type: {col_type}")
        else:
            # If no join analysis, add all tables
            for table in tables:
                schema_info.append(f"Table: {table}")
                for column, col_type in table_schemas[table].items():
                    schema_info.append(f"  Column: {column}, Type: {col_type}")
    
        if schema_info:
            if context:
                context += "\n\nDatabase Schema Information:\n" + "\n".join(schema_info)
            else:
                context = "Database Schema Information:\n" + "\n".join(schema_info)
        
        # Add join recommendations if available
        if join_analysis and join_analysis.get("join_recommendations"):
            context += "\n\nRecommended Joins:\n" + "\n".join(join_analysis["join_recommendations"])
        # Otherwise use our heuristic join detection
        elif len(tables) > 1:
            join_info = self._identify_potential_join_keys(table_schemas)
            if join_info:
                context += "\n\nPotential Table Relationships:\n" + "\n".join(join_info)
    
        # Create prompt for GPT with enhanced join guidance
        prompt = f"""
        Generate a SQL query for SQLite that answers the following question:
        
        Question: "{query}"
        
        {context}
        
        Available Tables: {', '.join(tables)}
        
        Important Guidelines:
        1. The query must use valid SQLite syntax
        2. Do not use functions not supported by SQLite (like MEDIAN)
        3. If the query requires data from multiple tables, use appropriate JOINs with the correct join conditions
        4. Use the EXACT table names as provided: {', '.join(tables)}
        5. DO NOT use aliases like 'h' or 't' unless necessary for joins
        6. When using aliases, make sure they are clear and descriptive (e.g., use '{tables[0]}' instead of 'h')
        7. Make sure all column references in JOINs are fully qualified with table names or aliases
        8. Return ONLY the SQL query with no additional text or explanation
        
        {join_analysis.get('query_guidance', '') if join_analysis else ''}
        """
        
        # Add reasoning about the query to help with debugging
        self._add_reasoning_step(
            "SQL Generation", 
            f"Generating SQL query for: '{query}'\n" + 
            f"Available tables: {', '.join(tables)}\n" + 
            (f"Join analysis: {join_analysis['summary']}" if join_analysis and join_analysis.get('summary') else "No join analysis available.")
        )
    
        # Query GPT with enhanced system prompt for SQL generation
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
            messages=[
                {"role": "system", "content": """You are an expert SQL query generator specializing in complex joins and multi-table queries.
                Your strength is understanding database schemas and creating efficient, accurate SQL queries with proper join conditions.
                You always use the EXACT table names as provided. DO NOT use aliases like 'h' or 't' unless necessary for joins.
                When multiple tables are involved, you carefully analyze the relationships between tables to create correct join conditions."""},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        # Extract SQL query
        sql_query = response.choices[0].message.content.strip()
        
        # Clean up SQL query (remove markdown formatting if present)
        sql_query = re.sub(r'^```sql\s*', '', sql_query)
        sql_query = re.sub(r'\s*```$', '', sql_query)
        
        # Add the SQL query to our reasoning steps
        self._add_reasoning_step(
            "Generated SQL", 
            f"```sql\n{sql_query}\n```"
        )
        
        return sql_query.strip()
    
    def _execute_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results with enhanced error handling.
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            List of dictionaries containing the results
        """
        # Check if database connection is established
        if not self.db_conn:
            error_msg = "Database connection not established. Please upload a file first."
            self._add_reasoning_step("Database Error", error_msg)
            print(f"Database connection error: {error_msg}")
            raise ValueError(error_msg)
        
        # Clean the SQL query to remove any problematic characters or formatting
        sql_query = sql_query.strip()
        
        # Add reasoning step about the SQL query being executed
        self._add_reasoning_step(
            "SQL Execution",
            f"Executing SQL query:\n```sql\n{sql_query}\n```"
        )
        
        # Debug information
        print(f"Executing SQL query: {sql_query}")
        print(f"Database path: {self.db_path}")
        
        # Check if the query contains specific patterns
        has_join = re.search(r'\bjoin\b', sql_query, re.IGNORECASE) is not None
        has_race = re.search(r'\brace\b|\bethnic', sql_query, re.IGNORECASE) is not None
        has_gender = re.search(r'\bgender\b|\bsex\b', sql_query, re.IGNORECASE) is not None
        has_aggregation = re.search(r'\bcount\b|\bsum\b|\bavg\b|\bmax\b|\bmin\b', sql_query, re.IGNORECASE) is not None
        
        # Add specific reasoning for demographic analysis
        if has_race or has_gender:
            self._add_reasoning_step(
                "Demographic Analysis",
                "This query involves demographic analysis. Ensuring proper handling of demographic data."
            )
        
        try:
            # Verify database connection is still valid
            if not self.db_conn:
                self._connect_to_db()
                if not self.db_conn:
                    raise ValueError("Failed to reconnect to database")
            
            cursor = self.db_conn.cursor()
            cursor.execute(sql_query)
            
            # Fetch results and convert to list of dictionaries
            rows = cursor.fetchall()
            print(f"Query returned {len(rows)} rows")
            
            if not rows:
                self._add_reasoning_step("SQL Results", "Query returned no results.")
                return []
            
            # Get column names from cursor description
            column_names = [description[0] for description in cursor.description]
            print(f"Column names: {column_names}")
            
            # Convert rows to dictionaries
            results = []
            for row in rows:
                row_dict = {column_names[i]: value for i, value in enumerate(row)}
                results.append(row_dict)
            
            # Print first row for debugging
            if results:
                print(f"First row of results: {results[0]}")
            
            # Add reasoning about the results
            if results:
                result_count = len(results)
                sample_result = results[0] if results else {}
                columns = list(sample_result.keys())
                
                # Build detailed reasoning about the results
                reasoning = f"Query returned {result_count} results with columns: {', '.join(columns)}\n"
                
                # Add insights based on query type
                if has_join:
                    reasoning += "This query used JOINs to combine data from multiple tables.\n"
                if has_aggregation:
                    reasoning += "This query used aggregation functions to summarize data.\n"
                if has_race:
                    reasoning += "This query analyzed race/ethnicity demographics.\n"
                if has_gender:
                    reasoning += "This query analyzed gender demographics.\n"
                
                self._add_reasoning_step("SQL Results", reasoning)
            
            return results
            
        except sqlite3.OperationalError as e:
            error_msg = str(e)
            detailed_error = f"SQLite operational error: {error_msg}."
            
            # Add more specific error details based on error message
            if "no such table" in error_msg.lower():
                detailed_error += " The table specified in the query does not exist in the database."
            elif "no such column" in error_msg.lower():
                detailed_error += " The column name in the query does not exist in the table."
            elif "syntax error" in error_msg.lower():
                detailed_error += " There is a syntax error in the SQL query."
            else:
                detailed_error += " This may be due to an invalid column name, table name, or syntax error."
            
            self._add_reasoning_step("SQL Error", detailed_error)
            print(f"SQLite operational error: {error_msg}")
            raise ValueError(f"SQL execution error: {error_msg}. {detailed_error}")
            
        except sqlite3.Error as e:
            error_msg = str(e)
            self._add_reasoning_step(
                "SQLite Error",
                f"SQLite error: {error_msg}. This is a database-specific error."
            )
            print(f"SQLite error: {error_msg}")
            raise ValueError(f"SQLite error: {error_msg}")
            
        except Exception as e:
            error_msg = str(e)
            self._add_reasoning_step(
                "SQL Error",
                f"Error executing SQL query: {error_msg}"
            )
            print(f"Error executing SQL: {error_msg}")
            raise ValueError(f"Error executing SQL query: {error_msg}")

    
    def _generate_python_code(self, query: str) -> str:
        """
        Generate Python code to answer a query.
        
{{ ... }}
        Args:
            query: The natural language query
            
        Returns:
            Python code string
        """
        # Prepare context from data dictionary if available
        context = ""
        if self.data_dict:
            fields_info = []
            for field in self.data_dict:
                if field not in ["dataset_name", "description", "fields_count"]:
                    field_data = self.data_dict[field]
                    fields_info.append(f"Field: {field}")
                    fields_info.append(f"  Type: {field_data.get('type', 'unknown')}")
                    fields_info.append(f"  Description: {field_data.get('description', 'No description')}")
            
            if fields_info:
                context = "Data Dictionary Information:\n" + "\n".join(fields_info)
        
        # Create prompt for GPT
        prompt = f"""
        Generate Python code that answers the following question:
        
        Question: "{query}"
        
        {context}
        
        Important:
        1. The code should use pandas for data processing
        2. Assume the data is available in a pandas DataFrame called 'df'
        3. The code should return the final result
        4. Return ONLY the Python code with no additional text or explanation
        """
        
        # Query GPT
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
            messages=[
                {"role": "system", "content": "You are an AI assistant that generates Python code."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        # Extract Python code
        python_code = response.choices[0].message.content.strip()
        
        # Clean up Python code (remove markdown formatting if present)
        python_code = re.sub(r'^```python\s*', '', python_code)
        python_code = re.sub(r'\s*```$', '', python_code)
        
        return python_code.strip()
    
    def _execute_python(self, python_code: str) -> Any:
        """
        Execute Python code in a controlled environment.
        
        Args:
            python_code: The Python code to execute
            
        Returns:
            Results of the execution
        """
        # This is a simplified implementation
        # In a production environment, you would want to use a sandboxed execution environment
        
        # Create a local namespace with pandas and other necessary libraries
        local_namespace = {
            'pd': pd,
            'numpy': pd.np,
        }
        
        # If we have a database connection, load data into a DataFrame
        if self.db_conn:
            # Get list of tables
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Load the first table into a DataFrame
            if tables:
                table_name = tables[0]
                local_namespace['df'] = pd.read_sql_query(f"SELECT * FROM {table_name}", self.db_conn)
        
        # Execute the code
        exec(python_code, {}, local_namespace)
        
        # Look for a result variable
        result = None
        for var_name, var_value in local_namespace.items():
            if var_name not in ['pd', 'numpy', 'df'] and not var_name.startswith('_'):
                result = var_value
                break
        
        # If no result variable found, return the DataFrame if it was modified
        if result is None and 'df' in local_namespace:
            result = local_namespace['df']
        
        return result
    
    def _generate_subtasks(self, query: str) -> List[Dict[str, Any]]:
        """
        Break down a complex query into subtasks.
        
        Args:
            query: The complex query to break down
            
        Returns:
            List of subtask dictionaries
        """
        # Prepare context from data dictionary if available
        context = ""
        if self.data_dict:
            context = f"Dataset: {self.data_dict.get('dataset_name', 'Unknown')}\n"
            context += f"Description: {self.data_dict.get('description', 'No description')}\n"
            context += f"Fields: {', '.join([f for f in self.data_dict if f not in ['dataset_name', 'description', 'fields_count']])}"
        
        # Create prompt for GPT
        prompt = f"""
        Break down the following complex query into a series of subtasks:
        
        Query: "{query}"
        
        {context}
        
        For each subtask, provide:
        1. A description of what the subtask should accomplish
        2. The type of operation needed (SQL or Python)
        3. Dependencies on other subtasks (if any)
        
        Format your response as a JSON array of subtask objects, each with:
        - "id": A unique identifier for the subtask (e.g., "subtask1")
        - "description": A description of what the subtask should accomplish
        - "operation_type": Either "sql" or "python"
        - "dependencies": Array of subtask IDs this subtask depends on (can be empty)
        """
        
        # Query GPT
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
            messages=[
                {"role": "system", "content": "You are an AI assistant that breaks down complex queries into subtasks."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        # Parse response
        try:
            result = json.loads(response.choices[0].message.content)
            if isinstance(result, dict) and "subtasks" in result:
                return result["subtasks"]
            elif isinstance(result, list):
                return result
            else:
                return []
        except:
            # Return a default subtask if parsing fails
            return [{
                "id": "subtask1",
                "description": query,
                "operation_type": "sql",
                "dependencies": []
            }]
    
    def _create_execution_plan(self, subtasks: List[Dict[str, Any]]) -> None:
        """
        Create an execution plan from subtasks.
        
        Args:
            subtasks: List of subtask dictionaries
        """
        # Reset execution plan
        self.execution_plan = []
        
        # Create a dependency graph
        dependency_graph = {}
        for task in subtasks:
            task_id = task["id"]
            dependencies = task.get("dependencies", [])
            dependency_graph[task_id] = dependencies
        
        # Topologically sort tasks
        sorted_tasks = self._topological_sort(dependency_graph)
        
        # Create execution plan
        step_num = 1
        for task_id in sorted_tasks:
            task = next((t for t in subtasks if t["id"] == task_id), None)
            if task:
                operation_type = task.get("operation_type", "sql")
                description = task.get("description", "")
                
                if operation_type == "sql":
                    sql_query = self._generate_sql_query(description)
                    self.execution_plan.append({
                        "step": step_num,
                        "task_id": task_id,
                        "description": description,
                        "action": "execute_sql",
                        "query": sql_query
                    })
                else:  # python
                    python_code = self._generate_python_code(description)
                    self.execution_plan.append({
                        "step": step_num,
                        "task_id": task_id,
                        "description": description,
                        "action": "execute_python",
                        "code": python_code
                    })
                
                step_num += 1
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        Perform a topological sort on a dependency graph.
        
        Args:
            graph: Dependency graph as a dictionary
            
        Returns:
            Topologically sorted list of task IDs
        """
        # Find all nodes
        nodes = set(graph.keys())
        for dependencies in graph.values():
            nodes.update(dependencies)
        
        # Initialize visit tracking
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(node):
            if node in temp_visited:
                # Cyclic dependency, skip
                return
            if node in visited:
                return
            
            temp_visited.add(node)
            
            # Visit dependencies
            for dependency in graph.get(node, []):
                visit(dependency)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        # Visit all nodes
        for node in nodes:
            if node not in visited:
                visit(node)
        
        # Reverse to get correct order
        return list(reversed(result))
    
    def _consolidate_results(self, results: List[Any]) -> Any:
        """
        Consolidate results from multiple steps.
        
        Args:
            results: List of results from each step
            
        Returns:
            Consolidated results
        """
        # If only one result, return it
        if len(results) == 1:
            return results[0]
        
        # If all results are dataframes, try to merge them
        all_dfs = all(isinstance(r, pd.DataFrame) for r in results)
        if all_dfs:
            try:
                # Concatenate dataframes
                return pd.concat(results, ignore_index=True)
            except:
                pass
        
        # Otherwise, return list of results
        return results
    
    def _generate_summary(self, query: str, results: Any) -> str:
        """
        Generate a summary of the results.
        
        Args:
            query: The original query
            results: The results to summarize
            
        Returns:
            Summary string
        """
        # Convert results to a string representation
        if isinstance(results, pd.DataFrame):
            results_str = results.to_string()
            if len(results_str) > 1000:
                results_str = results_str[:1000] + "...\n[truncated]"
        elif isinstance(results, list):
            if all(isinstance(item, dict) for item in results):
                results_str = json.dumps(results, indent=2)
                if len(results_str) > 1000:
                    results_str = results_str[:1000] + "...\n[truncated]"
            else:
                results_str = str(results)
        else:
            results_str = str(results)
        
        # Create prompt for GPT
        prompt = f"""
        Generate a concise summary of the following query results:
        
        Query: "{query}"
        
        Results:
        {results_str}
        
        Provide a clear, informative summary that answers the original query based on these results.
        """
        
        # Query GPT
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
            messages=[
                {"role": "system", "content": "You are an AI assistant that summarizes query results."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        
        # Return summary
        return response.choices[0].message.content.strip()
    
    def _add_reasoning_step(self, step_name: str, description: str) -> None:
        """
        Add a reasoning step to track the system's thought process.
        
        Args:
            step_name: Name of the reasoning step
            description: Description of the reasoning
        """
        self.reasoning_steps.append({
            "step_number": len(self.reasoning_steps) + 1,
            "step_name": step_name,
            "description": description
        })
    
    def _get_table_name(self) -> str:
        """
        Get the name of the table in the SQLite database.
        If multiple tables exist, returns the first one.
        
        Returns:
            Table name as a string
        """
        tables = self._get_all_tables()
        return tables[0]
    
    def _get_all_tables(self) -> List[str]:
        """
        Get all table names in the SQLite database.
        
        Returns:
            List of table names as strings
        """
        if not self.db_conn:
            print("Error: No database connection when getting tables")
            raise ValueError("No database connection established")
        
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Print raw table data for debugging
        print(f"Raw table data from database: {tables}")
        
        # Filter out system tables
        table_names = [row[0] for row in tables if row[0] != 'sqlite_sequence']
        
        print(f"Found tables in database: {table_names}")
        
        if not table_names:
            print("No tables found in database")
            raise ValueError("No tables found in database")
        
        return table_names
        
    def _get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Get the schema (column names and types) for a specific table.
        
        Args:
            table_name: Name of the table
        
        Returns:
            Dictionary mapping column names to their SQLite types
        """
        if not self.db_conn:
            return {}
            
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Create a dictionary of column name to type
            schema = {}
            for col in columns:
                # col[1] is name, col[2] is type
                schema[col[1]] = col[2]
                
            return schema
        except Exception as e:
            print(f"Error getting schema for table {table_name}: {str(e)}")
            return {}
    
    def _query_might_need_join(self, query: str, tables: List[str]) -> bool:
        """
        Detect if a query might need joins based on keywords.
        
        Args:
            query: The query to analyze
            tables: List of available tables
        
        Returns:
            True if the query might need joins, False otherwise
        """
        # Simple keyword-based detection
        keywords = ["join", "merge", "combine", "union", "intersect", "between", "relate", "relationship"]
        for keyword in keywords:
            if keyword in query.lower():
                return True
        
        # Check if query mentions multiple tables
        mentioned_tables = 0
        for table in tables:
            if table.lower() in query.lower():
                mentioned_tables += 1
                if mentioned_tables > 1:
                    return True
        
        # Check for common join patterns in natural language
        join_patterns = [
            r"\b(from|in)\s+\w+\s+(and|with)\s+\w+\b",  # "from table1 and table2"
            r"\b(data|information|records)\s+(from|in)\s+both\b",  # "data from both"
            r"\bcombine\s+\w+\s+(with|and)\s+\w+\b",  # "combine X with Y"
            r"\brelationship\s+between\b",  # "relationship between"
            r"\bconnect\s+\w+\s+(to|with)\s+\w+\b"  # "connect X to Y"
        ]
        
        for pattern in join_patterns:
            if re.search(pattern, query.lower()):
                return True
        
        return False
        
    def _identify_potential_join_keys(self, table_schemas: Dict[str, Dict[str, str]]) -> List[str]:
        """
        Identify potential join keys between tables based on column names and types.
        
        Args:
            table_schemas: Dictionary mapping table names to their column schemas
            
            table_schemas: Dictionary of table schemas
        
        Returns:
            List of potential join key descriptions
        """
        # Simple detection based on column names
        join_keys = []
        for table1, schema1 in table_schemas.items():
            for table2, schema2 in table_schemas.items():
                if table1 != table2:
                    for col1, type1 in schema1.items():
                        for col2, type2 in schema2.items():
                            if col1 == col2 and type1 == type2:
                                join_keys.append(f"Potential join key: {col1} ({table1} and {table2})")
        
        return join_keys
    
    def close(self) -> None:
        """Close database connection and clean up resources."""
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None

# Example usage
if __name__ == "__main__":
    processor = AgenticQueryProcessor(
        data_dict_path="data_dictionary.json",
        db_path="database.db"
    )
    
    # Process a query
    result = processor.process_query("What is the average value by category?")
    
    # Print summary
    print(f"Query: {result['query']}")
    print(f"Complexity: {result['complexity']}")
    print(f"Summary: {result['summary']}")
    print("\nReasoning Steps:")
    for step in result['reasoning_steps']:
        print(f"{step['step_number']}. {step['step_name']}: {step['description']}")
    
    # Clean up
    processor.close()
