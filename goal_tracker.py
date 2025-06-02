"""
Goal Tracker for the Agentic NL2SQL system.
Manages goals, subgoals, and their execution state.
"""

import os
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from utils import clean_yaml_response, agent_activity

class GoalTemplate:
    """Defines a goal template with parameters and execution plan."""
    
    def __init__(self, name: str, description: str, parameters: List[str] = None):
        """
        Initialize a goal template.
        
        Args:
            name: The name of the goal template
            description: Description of what this goal accomplishes
            parameters: List of parameter names required for this goal
        """
        self.name = name
        self.description = description
        self.parameters = parameters or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the goal template to a dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GoalTemplate':
        """Create a goal template from a dictionary."""
        return cls(
            name=data['name'],
            description=data['description'],
            parameters=data.get('parameters', [])
        )


class GoalTracker:
    """Tracks goals, their state, and execution history."""
    
    def __init__(self):
        """Initialize the goal tracker."""
        self.goals = {}  # Dictionary of goal_id -> goal_data
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, GoalTemplate]:
        """Initialize the built-in goal templates."""
        templates = {}
        
        # Process query goal template
        templates['process_query'] = GoalTemplate(
            name='process_query',
            description='Process a natural language query and return results',
            parameters=['query']
        )
        
        # Process file goal template
        templates['process_file'] = GoalTemplate(
            name='process_file',
            description='Process an uploaded file and create a database',
            parameters=['file_path']
        )
        
        # Generate sample queries goal template
        templates['generate_sample_queries'] = GoalTemplate(
            name='generate_sample_queries',
            description='Generate sample queries based on the data dictionary',
            parameters=['data_dict_path']
        )
        
        return templates
    
    def create_goal(self, template_name: str, parameters: Dict[str, Any]) -> str:
        """
        Create a new goal from a template.
        
        Args:
            template_name: Name of the goal template to use
            parameters: Dictionary of parameter values
            
        Returns:
            The ID of the created goal
        """
        if template_name not in self.templates:
            raise ValueError(f"Unknown goal template: {template_name}")
        
        template = self.templates[template_name]
        
        # Validate parameters
        for param in template.parameters:
            if param not in parameters:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Create goal ID
        goal_id = str(uuid.uuid4())
        
        # Create goal data
        goal_data = {
            'id': goal_id,
            'template': template_name,
            'title': f"{template.name.replace('_', ' ').title()}: {parameters.get('query', '')}",
            'description': template.description,
            'parameters': parameters,
            'state': 'created',
            'created_at': time.time(),
            'updated_at': time.time(),
            'subgoals': [],
            'reasoning_steps': [],
            'result': None
        }
        
        # Store the goal
        self.goals[goal_id] = goal_data
        
        # Log goal creation
        agent_activity('GoalTracker', 'GOAL_CREATED', f"Created goal: {goal_data['title']}")
        
        return goal_id
    
    def get_goal(self, goal_id: str) -> Dict[str, Any]:
        """
        Get a goal by ID.
        
        Args:
            goal_id: The ID of the goal
            
        Returns:
            The goal data
        """
        if goal_id not in self.goals:
            raise ValueError(f"Unknown goal ID: {goal_id}")
        
        return self.goals[goal_id]
    
    def update_goal_state(self, goal_id: str, state: str) -> None:
        """
        Update the state of a goal.
        
        Args:
            goal_id: The ID of the goal
            state: The new state
        """
        if goal_id not in self.goals:
            raise ValueError(f"Unknown goal ID: {goal_id}")
        
        goal = self.goals[goal_id]
        old_state = goal['state']
        goal['state'] = state
        goal['updated_at'] = time.time()
        
        # Log state change
        agent_activity('GoalTracker', 'GOAL_STATE_CHANGED', 
                      f"Goal state changed: {old_state} -> {state}", 
                      {'goal_id': goal_id, 'title': goal['title']})
    
    def add_reasoning_step(self, goal_id: str, step_name: str, description: str) -> None:
        """
        Add a reasoning step to a goal.
        
        Args:
            goal_id: The ID of the goal
            step_name: The name of the reasoning step
            description: Description of the reasoning step
        """
        if goal_id not in self.goals:
            raise ValueError(f"Unknown goal ID: {goal_id}")
        
        goal = self.goals[goal_id]
        
        # Create step data
        step_data = {
            'step_number': len(goal['reasoning_steps']) + 1,
            'step_name': step_name,
            'description': description,
            'timestamp': time.time()
        }
        
        # Add to reasoning steps
        goal['reasoning_steps'].append(step_data)
        goal['updated_at'] = time.time()
        
        # Log reasoning step
        agent_activity('GoalTracker', 'REASONING_STEP', 
                      f"Step {step_data['step_number']}: {step_name}", 
                      {'goal_id': goal_id, 'title': goal['title']})
    
    def add_subgoal(self, parent_goal_id: str, template_name: str, parameters: Dict[str, Any]) -> str:
        """
        Add a subgoal to a parent goal.
        
        Args:
            parent_goal_id: The ID of the parent goal
            template_name: Name of the goal template to use
            parameters: Dictionary of parameter values
            
        Returns:
            The ID of the created subgoal
        """
        if parent_goal_id not in self.goals:
            raise ValueError(f"Unknown parent goal ID: {parent_goal_id}")
        
        # Create the subgoal
        subgoal_id = self.create_goal(template_name, parameters)
        
        # Add reference to parent
        self.goals[subgoal_id]['parent_goal_id'] = parent_goal_id
        
        # Add to parent's subgoals
        parent_goal = self.goals[parent_goal_id]
        parent_goal['subgoals'].append(subgoal_id)
        parent_goal['updated_at'] = time.time()
        
        return subgoal_id
    
    def set_goal_result(self, goal_id: str, result: Any) -> None:
        """
        Set the result of a goal.
        
        Args:
            goal_id: The ID of the goal
            result: The result data
        """
        if goal_id not in self.goals:
            raise ValueError(f"Unknown goal ID: {goal_id}")
        
        goal = self.goals[goal_id]
        goal['result'] = result
        goal['updated_at'] = time.time()
        
        # Update state to completed
        self.update_goal_state(goal_id, 'completed')
        
        # Log result
        agent_activity('GoalTracker', 'GOAL_COMPLETED', 
                      f"Goal completed: {goal['title']}", 
                      {'goal_id': goal_id})
    
    def get_all_goals(self) -> List[Dict[str, Any]]:
        """
        Get all goals.
        
        Returns:
            List of all goals
        """
        return list(self.goals.values())
    
    def get_active_goals(self) -> List[Dict[str, Any]]:
        """
        Get all active goals (not completed or failed).
        
        Returns:
            List of active goals
        """
        return [goal for goal in self.goals.values() 
                if goal['state'] not in ['completed', 'failed']]
