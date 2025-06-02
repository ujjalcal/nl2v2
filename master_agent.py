"""
Master Agent for the Agentic NL2SQL system.
Orchestrates goals, subgoals, and specialized agents.
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional, Tuple, Union
import time

# Reuse the BaseAgent class
from agents import (
    BaseAgent, FileClassifierAgent, DataProfilerAgent, 
    DictionarySynthesizerAgent, ConversationalAgent,
    QueryNormalizerAgent, QueryDecomposerAgent,
    ExecutionPlannerAgent, ResultCombinerAgent
)

# Reuse the AgenticQueryProcessor
from agentic_processor import AgenticQueryProcessor

# Import the GoalTracker
from goal_tracker import GoalTracker

# Reuse utilities
from utils import clean_yaml_response, agent_activity, clean_sql_query

class MasterAgent(BaseAgent):
    """
    Master Agent that orchestrates the execution of goals using specialized agents.
    Follows a dynamic, goal-oriented approach rather than hardcoded workflows.
    """
    
    def __init__(self):
        """Initialize the Master Agent."""
        super().__init__(name="MasterAgent")
        
        # Initialize the goal tracker
        self.goal_tracker = GoalTracker()
        
        # Initialize worker agents - reuse existing agents
        self.worker_agents = {
            "file_classifier": FileClassifierAgent(),
            "data_profiler": DataProfilerAgent(),
            "dictionary_synthesizer": DictionarySynthesizerAgent(),
            "conversational": ConversationalAgent(),
            "query_normalizer": QueryNormalizerAgent(),
            "query_decomposer": QueryDecomposerAgent(),
            "execution_planner": ExecutionPlannerAgent(),
            "result_combiner": ResultCombinerAgent()
        }
        
        # Initialize tools - reuse existing processor
        self.query_processor = AgenticQueryProcessor()
        
        # Track current data context
        self.current_file_path = None
        self.current_db_path = None
        self.current_data_dict_path = None
    
    def create_goal(self, template_name: str, parameters: Dict[str, Any]) -> str:
        """
        Create a new goal.
        
        Args:
            template_name: Name of the goal template
            parameters: Parameters for the goal
            
        Returns:
            Goal ID
        """
        agent_activity(self.name, 'GOAL_CREATION', f"Creating goal: {template_name}")
        return self.goal_tracker.create_goal(template_name, parameters)
    
    def execute_goal(self, goal_id: str) -> Dict[str, Any]:
        """
        Execute a goal by dynamically planning and executing subgoals.
        
        Args:
            goal_id: The ID of the goal to execute
            
        Returns:
            Result of the goal execution
        """
        # Get the goal
        goal = self.goal_tracker.get_goal(goal_id)
        
        # Update goal state
        self.goal_tracker.update_goal_state(goal_id, 'executing')
        agent_activity(self.name, 'EXECUTING', f"Executing goal: {goal['title']}")
        
        # Add initial reasoning step
        self.goal_tracker.add_reasoning_step(
            goal_id, 
            "Goal Analysis", 
            f"Analyzing goal: {goal['title']}"
        )
        
        # Process based on goal template
        template_name = goal['template']
        
        if template_name == 'process_query':
            result = self._execute_process_query_goal(goal)
        elif template_name == 'process_file':
            result = self._execute_process_file_goal(goal)
        elif template_name == 'generate_sample_queries':
            result = self._execute_generate_sample_queries_goal(goal)
        else:
            # For unknown templates, use dynamic planning
            result = self._execute_dynamic_goal(goal)
        
        # Set goal result
        self.goal_tracker.set_goal_result(goal_id, result)
        
        # Generate summary
        summary = self._generate_goal_summary(goal_id)
        
        # Return the result
        return result
    
    def _execute_process_query_goal(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a process_query goal using the AgenticQueryProcessor.
        
        Args:
            goal: The goal data
            
        Returns:
            Query processing result
        """
        # Extract query from parameters
        query = goal['parameters']['query']
        
        # Add reasoning step
        self.goal_tracker.add_reasoning_step(
            goal['id'], 
            "Query Processing", 
            f"Processing query: {query}"
        )
        
        # Use the existing query processor - maximum reuse
        try:
            # Initialize with current context if available
            if self.current_data_dict_path and self.current_db_path:
                processor = AgenticQueryProcessor(
                    data_dict_path=self.current_data_dict_path,
                    db_path=self.current_db_path
                )
            else:
                processor = self.query_processor
            
            # Process the query
            result = processor.process_query(query)
            
            # Add reasoning step for result
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "Query Result", 
                f"Query processed successfully"
            )
            
            return result
        
        except Exception as e:
            # Handle errors
            error_message = str(e)
            
            # Add reasoning step for error
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "Error", 
                f"Error processing query: {error_message}"
            )
            
            # Return error result
            return {
                'success': False,
                'error': error_message,
                'query': query,
                'type': 'error'
            }
    
    def _execute_process_file_goal(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a process_file goal using the specialized agents.
        
        Args:
            goal: The goal data
            
        Returns:
            File processing result
        """
        # Extract file path from parameters
        file_path = goal['parameters']['file_path']
        
        # Add reasoning step
        self.goal_tracker.add_reasoning_step(
            goal['id'], 
            "File Processing", 
            f"Processing file: {file_path}"
        )
        
        try:
            # Step 1: Classify the file using FileClassifierAgent
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "File Classification", 
                f"Classifying file type and structure"
            )
            
            classification_result = self.worker_agents['file_classifier'].process(file_path)
            
            # Step 2: Profile the data using DataProfilerAgent
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "Data Profiling", 
                f"Profiling data patterns and statistics"
            )
            
            profile_result = self.worker_agents['data_profiler'].process(
                file_path, classification_result
            )
            
            # Step 3: Create data dictionary using DictionarySynthesizerAgent
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "Dictionary Creation", 
                f"Creating data dictionary from profiling results"
            )
            
            dictionary_result = self.worker_agents['dictionary_synthesizer'].process(
                profile_result, classification_result
            )
            
            # Save the data dictionary to a file
            dict_file_path = f"temp/data_dictionary_{time.strftime('%Y%m%d_%H%M%S')}.json"
            with open(dict_file_path, 'w') as f:
                json.dump(dictionary_result, f, indent=2)
            
            # Update current context
            self.current_file_path = file_path
            self.current_data_dict_path = dict_file_path
            
            # Create a database if needed
            if classification_result.get('content_type') == 'data':
                db_path = f"temp/database_{time.strftime('%Y%m%d_%H%M%S')}.db"
                
                # TODO: Create database from file
                # This would normally use the process_file function from nl2sql_api.py
                # For now, just set the path
                self.current_db_path = db_path
            
            # Add reasoning step for result
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "File Processing Result", 
                f"File processed successfully"
            )
            
            # Return success result
            return {
                'success': True,
                'file_path': file_path,
                'classification': classification_result,
                'profile': profile_result,
                'dictionary': dictionary_result,
                'data_dict_path': self.current_data_dict_path,
                'db_path': self.current_db_path
            }
        
        except Exception as e:
            # Handle errors
            error_message = str(e)
            
            # Add reasoning step for error
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "Error", 
                f"Error processing file: {error_message}"
            )
            
            # Return error result
            return {
                'success': False,
                'error': error_message,
                'file_path': file_path,
                'type': 'error'
            }
    
    def _execute_generate_sample_queries_goal(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a generate_sample_queries goal.
        
        Args:
            goal: The goal data
            
        Returns:
            Sample queries result
        """
        # Extract data dictionary path from parameters
        data_dict_path = goal['parameters'].get('data_dict_path', self.current_data_dict_path)
        
        if not data_dict_path:
            error_message = "No data dictionary available"
            
            # Add reasoning step for error
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "Error", 
                error_message
            )
            
            # Return error result
            return {
                'success': False,
                'error': error_message,
                'type': 'error'
            }
        
        # Add reasoning step
        self.goal_tracker.add_reasoning_step(
            goal['id'], 
            "Sample Query Generation", 
            f"Generating sample queries from data dictionary"
        )
        
        try:
            # Load the data dictionary
            with open(data_dict_path, 'r') as f:
                data_dict = json.load(f)
            
            # Create system prompt
            system_prompt = """
            You are an expert SQL query generator.
            Your task is to generate sample natural language queries that users might ask about the data.
            The queries should range from simple to complex and cover different aspects of the data.
            
            Respond with a YAML structure containing:
            - sample_queries: List of 5-10 natural language queries
            """
            
            # Create user message with data dictionary
            user_message = f"""
            Data Dictionary:
            {json.dumps(data_dict, indent=2)}
            
            Generate 5-10 sample natural language queries that users might ask about this data.
            Include a mix of simple and complex queries.
            """
            
            # Call LLM
            content = self._call_llm(system_prompt, user_message)
            result = self._parse_yaml_response(content, {
                'sample_queries': [
                    "What tables are in the database?",
                    "Show me the first 10 rows of data",
                    "What is the total count of records?",
                    "What are the column names?",
                    "Show me some basic statistics about the data"
                ]
            })
            
            # Add reasoning step for result
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "Sample Queries Generated", 
                f"Generated {len(result.get('sample_queries', []))} sample queries"
            )
            
            # Return success result
            return {
                'success': True,
                'sample_queries': result.get('sample_queries', []),
                'data_dict_path': data_dict_path,
                'type': 'sample_queries'
            }
        
        except Exception as e:
            # Handle errors
            error_message = str(e)
            
            # Add reasoning step for error
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                "Error", 
                f"Error generating sample queries: {error_message}"
            )
            
            # Return error result
            return {
                'success': False,
                'error': error_message,
                'type': 'error'
            }
    
    def _execute_dynamic_goal(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a goal using dynamic planning.
        
        Args:
            goal: The goal data
            
        Returns:
            Goal execution result
        """
        # Add reasoning step
        self.goal_tracker.add_reasoning_step(
            goal['id'], 
            "Dynamic Planning", 
            f"Creating dynamic plan for goal: {goal['title']}"
        )
        
        # Create plan using LLM
        plan = self._create_dynamic_plan(goal)
        
        # Add reasoning step for plan
        self.goal_tracker.add_reasoning_step(
            goal['id'], 
            "Execution Plan", 
            f"Plan created with {len(plan.get('steps', []))} steps"
        )
        
        # Execute each step in the plan
        results = {}
        for i, step in enumerate(plan.get('steps', [])):
            step_number = i + 1
            step_name = step.get('name', f"Step {step_number}")
            
            # Add reasoning step for this plan step
            self.goal_tracker.add_reasoning_step(
                goal['id'], 
                f"Step {step_number}: {step_name}", 
                step.get('description', 'Executing step')
            )
            
            # Execute the step based on its type
            step_type = step.get('type', 'unknown')
            step_params = step.get('parameters', {})
            
            try:
                if step_type == 'agent':
                    # Use a worker agent
                    agent_name = step_params.get('agent')
                    if agent_name in self.worker_agents:
                        agent = self.worker_agents[agent_name]
                        step_result = agent.process(**step_params.get('args', {}))
                    else:
                        step_result = {'error': f"Unknown agent: {agent_name}"}
                
                elif step_type == 'subgoal':
                    # Create and execute a subgoal
                    subgoal_template = step_params.get('template')
                    subgoal_params = step_params.get('parameters', {})
                    subgoal_id = self.goal_tracker.add_subgoal(
                        goal['id'], subgoal_template, subgoal_params
                    )
                    step_result = self.execute_goal(subgoal_id)
                
                else:
                    # Unknown step type
                    step_result = {'error': f"Unknown step type: {step_type}"}
                
                # Store the result
                results[f"step_{step_number}"] = step_result
                
                # Add reasoning step for step result
                self.goal_tracker.add_reasoning_step(
                    goal['id'], 
                    f"Step {step_number} Result", 
                    f"Step completed successfully"
                )
            
            except Exception as e:
                # Handle step error
                error_message = str(e)
                
                # Add reasoning step for error
                self.goal_tracker.add_reasoning_step(
                    goal['id'], 
                    f"Step {step_number} Error", 
                    f"Error executing step: {error_message}"
                )
                
                # Store the error
                results[f"step_{step_number}"] = {
                    'error': error_message,
                    'type': 'error'
                }
                
                # Check if we should continue or abort
                if step.get('critical', False):
                    # Critical step failed, abort plan
                    self.goal_tracker.add_reasoning_step(
                        goal['id'], 
                        "Plan Aborted", 
                        f"Critical step {step_number} failed, aborting plan"
                    )
                    break
        
        # Combine results
        combined_result = {
            'success': all(not r.get('error') for r in results.values()),
            'plan': plan,
            'results': results,
            'type': 'dynamic'
        }
        
        return combined_result
    
    def _create_dynamic_plan(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a dynamic execution plan for a goal using LLM.
        
        Args:
            goal: The goal data
            
        Returns:
            Execution plan
        """
        # Create system prompt
        system_prompt = """
        You are an expert planner for a natural language to SQL system.
        Your task is to create a step-by-step execution plan for a goal.
        Each step should use either an agent or a subgoal.
        
        Available agents:
        - file_classifier: Identifies file type and structure
        - data_profiler: Analyzes data patterns, types, and statistics
        - dictionary_synthesizer: Creates schema/dictionary from profiled data
        - conversational: Manages multi-turn conversations and query clarification
        - query_normalizer: Standardizes and cleans queries
        - query_decomposer: Breaks down complex queries into sub-queries
        - execution_planner: Creates execution plans for hybrid SQL/Python processing
        - result_combiner: Joins results from multiple execution paths
        
        Available subgoal templates:
        - process_query: Process a natural language query and return results
        - process_file: Process an uploaded file and create a database
        - generate_sample_queries: Generate sample queries based on the data dictionary
        
        Respond with a YAML structure containing:
        - goal_analysis: Your analysis of the goal
        - steps: List of steps to execute
          - name: Step name
          - description: Step description
          - type: 'agent' or 'subgoal'
          - parameters: Parameters for the agent or subgoal
          - critical: Whether this step is critical (failure aborts the plan)
        """
        
        # Create user message with goal details
        user_message = f"""
        Goal: {goal['title']}
        Description: {goal['description']}
        Parameters: {json.dumps(goal['parameters'], indent=2)}
        
        Create a step-by-step execution plan for this goal.
        """
        
        # Call LLM
        content = self._call_llm(system_prompt, user_message)
        plan = self._parse_yaml_response(content, {
            'goal_analysis': f"Analysis for goal: {goal['title']}",
            'steps': []
        })
        
        return plan
    
    def _generate_goal_summary(self, goal_id: str) -> str:
        """
        Generate a summary of a goal execution.
        
        Args:
            goal_id: The ID of the goal
            
        Returns:
            Summary string
        """
        # Get the goal
        goal = self.goal_tracker.get_goal(goal_id)
        
        # Create system prompt
        system_prompt = """
        You are an expert summarizer for a natural language to SQL system.
        Your task is to create a concise summary of a goal execution.
        The summary should highlight key steps, results, and any issues encountered.
        
        Respond with a brief paragraph summarizing the goal execution.
        """
        
        # Create user message with goal details
        user_message = f"""
        Goal: {goal['title']}
        Description: {goal['description']}
        State: {goal['state']}
        
        Reasoning Steps:
        {yaml.dump(goal['reasoning_steps'])}
        
        Result:
        {yaml.dump(goal['result'])}
        
        Create a concise summary of this goal execution.
        """
        
        # Call LLM
        summary = self._call_llm(system_prompt, user_message)
        
        # Clean up the summary
        summary = summary.replace('```', '').strip()
        
        return summary
    
    def get_goal_status(self, goal_id: str) -> Dict[str, Any]:
        """
        Get the status of a goal.
        
        Args:
            goal_id: The ID of the goal
            
        Returns:
            Goal status
        """
        # Get the goal
        goal = self.goal_tracker.get_goal(goal_id)
        
        # Create status object
        status = {
            'id': goal['id'],
            'title': goal['title'],
            'state': goal['state'],
            'created_at': goal['created_at'],
            'updated_at': goal['updated_at'],
            'reasoning_step_count': len(goal['reasoning_steps']),
            'subgoal_count': len(goal['subgoals']),
            'has_result': goal['result'] is not None
        }
        
        return status
    
    def get_all_goals(self) -> List[Dict[str, Any]]:
        """
        Get all goals.
        
        Returns:
            List of all goals
        """
        return self.goal_tracker.get_all_goals()
    
    def get_active_goals(self) -> List[Dict[str, Any]]:
        """
        Get all active goals.
        
        Returns:
            List of active goals
        """
        return self.goal_tracker.get_active_goals()


# Example usage
if __name__ == "__main__":
    # Initialize the master agent
    master_agent = MasterAgent()
    
    # Create a goal
    goal_id = master_agent.create_goal('process_query', {'query': 'What is the average salary by department?'})
    
    # Execute the goal
    result = master_agent.execute_goal(goal_id)
    
    # Print the result
    print(f"Goal executed: {result}")
