import os
import json
import yaml
import sqlite3
import pandas as pd
from typing import Dict, Any, Optional, List, Union, Tuple

from utils import agent_activity
from agents import (
    QueryClassifierAgent,
    QueryNormalizerAgent,
    QueryDecomposerAgent,
    SQLGeneratorAgent,
    SQLExecutorAgent,
    ResultCombinerAgent
)

class QueryProcessingAgent:
    """
    Unified agent for handling all query processing tasks from natural language to results.
    Coordinates the work of specialized sub-agents for each step of the query processing pipeline.
    """
    
    def __init__(self):
        """Initialize the QueryProcessingAgent with its sub-agents."""
        self.name = "QueryProcessingAgent"
        
        # Initialize sub-agents
        self.query_classifier = QueryClassifierAgent()
        self.query_normalizer = QueryNormalizerAgent()
        self.query_decomposer = QueryDecomposerAgent()
        self.sql_generator = SQLGeneratorAgent()
        self.sql_executor = SQLExecutorAgent()
        self.result_combiner = ResultCombinerAgent()
        
        # Track reasoning steps
        self.reasoning_steps = []
        
        # Track current state
        self.current_state = "IDLE"
    
    def process_query(self, query: str, db_path: str, data_dict_path: str) -> Dict[str, Any]:
        """
        Process a natural language query through the entire pipeline.
        
        Args:
            query: The natural language query to process
            db_path: Path to the SQLite database
            data_dict_path: Path to the data dictionary JSON file
            
        Returns:
            Dictionary with query results including SQL, data, and summary
        """
        agent_activity(self.name, 'PROCESSING', f'Processing query: {query}')
        self._update_state("PROCESSING")
        self._add_reasoning_step("Query Analysis", f"Analyzing query: '{query}'")
        
        # Load data dictionary for context
        data_dict = self._load_data_dictionary(data_dict_path)
        
        # Step 1: Classify the query (SQL needed or direct answer)
        agent_activity(self.name, 'CLASSIFYING', 'Classifying query')
        classification = self.query_classifier.process(query, data_dict)
        query_type = classification.get('query_type', 'sql')
        confidence = classification.get('confidence', 0.5)
        
        self._add_reasoning_step("Query Classification", 
                               f"Query type: {query_type}, Confidence: {confidence}")
        
        # Handle direct questions without SQL if confidence is high enough
        if query_type == 'direct' and confidence >= 0.7:
            agent_activity(self.name, 'DIRECT_RESPONSE', 'Generating direct response')
            return self._process_direct_query(query, classification, data_dict)
        
        # Step 2: Normalize the query
        agent_activity(self.name, 'NORMALIZING', 'Normalizing query')
        normalized = self.query_normalizer.process(query, self._get_table_info(db_path))
        self._add_reasoning_step("Query Normalization", 
                               f"Normalized query: '{normalized.get('normalized_query', query)}'")
        
        # Step 3: Analyze complexity and decompose if needed
        complexity = normalized.get('complexity', 'simple')
        self._add_reasoning_step("Complexity Analysis", f"Query complexity: {complexity}")
        
        if complexity == 'complex':
            # Decompose complex query
            agent_activity(self.name, 'DECOMPOSING', 'Decomposing complex query')
            decomposed = self.query_decomposer.process(
                normalized.get('normalized_query', query),
                normalized,
                self._get_table_info(db_path)
            )
            self._add_reasoning_step("Query Decomposition", 
                                   f"Decomposed into {len(decomposed.get('sub_queries', []))} sub-queries")
            
            # Process each sub-query
            results = {}
            for i, sub_query in enumerate(decomposed.get('sub_queries', [])):
                sub_result = self._process_simple_query(
                    sub_query.get('query', ''),
                    db_path,
                    data_dict
                )
                results[f"sub_query_{i}"] = sub_result
            
            # Combine results
            agent_activity(self.name, 'COMBINING', 'Combining sub-query results')
            combined = self.result_combiner.process(
                results,
                decomposed,
                query
            )
            
            self._update_state("DONE")
            return {
                "success": True,
                "query": query,
                "query_type": "complex",
                "sql": None,  # Multiple SQL queries were used
                "data": combined.get('result', {}),
                "summary": combined.get('summary', ''),
                "reasoning_steps": self.reasoning_steps
            }
        else:
            # Process simple query directly
            return self._process_simple_query(
                normalized.get('normalized_query', query),
                db_path,
                data_dict
            )
    
    def _process_simple_query(self, query: str, db_path: str, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a simple query that doesn't need decomposition.
        
        Args:
            query: The normalized query to process
            db_path: Path to the SQLite database
            data_dict: The data dictionary
            
        Returns:
            Dictionary with query results
        """
        # Step 1: Generate SQL
        agent_activity(self.name, 'GENERATING_SQL', 'Generating SQL query')
        table_info = self._get_table_info(db_path)
        sql_result = self.sql_generator.process(query, table_info, data_dict)
        
        sql = sql_result.get('sql', '')
        reasoning = sql_result.get('reasoning', '')
        
        self._add_reasoning_step("SQL Generation", f"Generated SQL: {sql}")
        self._add_reasoning_step("SQL Reasoning", reasoning)
        
        # Step 2: Execute SQL
        agent_activity(self.name, 'EXECUTING_SQL', 'Executing SQL query')
        execution_result = self.sql_executor.process(sql, db_path)
        
        if not execution_result.get('success', False):
            error = execution_result.get('error', 'Unknown error')
            self._add_reasoning_step("SQL Execution", f"Error: {error}")
            self._update_state("ERROR")
            return {
                "success": False,
                "query": query,
                "sql": sql,
                "error": error,
                "reasoning_steps": self.reasoning_steps
            }
        
        # Step 3: Generate summary
        agent_activity(self.name, 'SUMMARIZING', 'Generating result summary')
        summary = self._generate_summary(query, sql, execution_result)
        
        self._add_reasoning_step("Result Summary", "Generated natural language summary of results")
        self._update_state("DONE")
        
        return {
            "success": True,
            "query": query,
            "sql": sql,
            "data": execution_result.get('records', []),  # Use 'records' key instead of 'dataframe'
            "columns": execution_result.get('columns', []),
            "summary": summary,
            "reasoning_steps": self.reasoning_steps
        }
    
    def _process_direct_query(self, query: str, classification: Dict[str, Any], 
                             data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a direct question that doesn't require SQL.
        
        Args:
            query: The original query
            classification: The query classification results
            data_dict: The data dictionary
            
        Returns:
            Dictionary with direct response
        """
        agent_activity(self.name, 'DIRECT_RESPONSE', 'Generating direct response')
        
        # Use the response from the classifier if available
        direct_response = classification.get('response', '')
        if not direct_response:
            # Generate a response using the data dictionary context
            system_prompt = """
            You are a helpful assistant answering questions about a database.
            Provide a concise, accurate response to the user's question using the data dictionary context.
            Do not make up information that isn't supported by the context.
            """
            
            user_message = f"""
            Question: {query}
            
            Data Dictionary Context:
            {json.dumps(data_dict, indent=2)}
            
            Please provide a direct answer to this question based on the data dictionary context.
            """
            
            # This would normally call the LLM, but we'll simulate it for now
            direct_response = f"This is a direct response to: {query}"
        
        self._add_reasoning_step("Direct Response", "Generated direct response without SQL")
        self._update_state("DONE")
        
        return {
            "success": True,
            "query": query,
            "query_type": "direct",
            "sql": None,
            "data": None,
            "summary": direct_response,
            "reasoning_steps": self.reasoning_steps
        }
    
    def _generate_summary(self, query: str, sql: str, execution_result: Dict[str, Any]) -> str:
        """
        Generate a natural language summary of the query results.
        
        Args:
            query: The original query
            sql: The SQL query that was executed
            execution_result: The execution results
            
        Returns:
            Natural language summary
        """
        if not execution_result.get('success', False):
            return f"Error executing query: {execution_result.get('error', 'Unknown error')}"
        
        records = execution_result.get('records', [])
        columns = execution_result.get('columns', [])
        
        if not records:
            return "The query returned no results."
        
        # For simple results, create a basic summary
        if len(records) == 1 and len(columns) == 1:
            return f"The result is {records[0][columns[0]]}."
        
        # For more complex results, we would normally use LLM
        row_count = len(records)
        col_count = len(columns)
        return f"The query returned {row_count} rows with {col_count} columns."
    
    def _get_table_info(self, db_path: str) -> Dict[str, List[str]]:
        """
        Get table information from the database.
        
        Args:
            db_path: Path to the SQLite database
            
        Returns:
            Dictionary mapping table names to their columns
        """
        try:
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
            
            conn.close()
            return table_info
            
        except Exception as e:
            agent_activity(self.name, 'ERROR', f'Error getting table info: {str(e)}')
            return {}
    
    def _load_data_dictionary(self, path: str) -> Dict[str, Any]:
        """
        Load a data dictionary from a JSON file.
        
        Args:
            path: Path to the data dictionary JSON file
            
        Returns:
            Data dictionary object
        """
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            agent_activity(self.name, 'ERROR', f'Error loading data dictionary: {str(e)}')
            return {}
    
    def _add_reasoning_step(self, step_name: str, description: str) -> None:
        """
        Add a reasoning step to track the agent's thought process.
        
        Args:
            step_name: Name of the reasoning step
            description: Description of the reasoning
        """
        self.reasoning_steps.append({
            "step_number": len(self.reasoning_steps) + 1,
            "step_name": step_name,
            "description": description
        })
    
    def _update_state(self, new_state: str) -> None:
        """
        Update the current workflow state.
        
        Args:
            new_state: The new state to transition to
        """
        agent_activity(self.name, 'STATE_CHANGE', f'State change: {self.current_state} -> {new_state}')
        self.current_state = new_state
