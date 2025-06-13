import os
import json
import yaml
import sqlite3
import pandas as pd
from typing import Dict, Any, Optional, List

from utils import agent_activity
from agents import (
    FileClassifierAgent,
    DataProfilerAgent,
    DictionarySynthesizerAgent
)

class DataProcessingAgent:
    """
    Unified agent for handling all data processing tasks from file upload to database creation.
    Coordinates the work of specialized sub-agents for each step of the data processing pipeline.
    """
    
    def __init__(self):
        """Initialize the DataProcessingAgent with its sub-agents."""
        self.name = "DataProcessingAgent"
        
        # Initialize sub-agents
        self.file_classifier = FileClassifierAgent()
        self.data_profiler = DataProfilerAgent()
        self.dictionary_synthesizer = DictionarySynthesizerAgent()
        
        # Track the current workflow state
        self.current_state = "IDLE"
        
        # Track artifacts
        self.artifacts = {}
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a file through the entire data processing pipeline.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Dictionary with processing results including classification, profile,
            dictionary, and database path
        """
        agent_activity(self.name, 'PROCESSING', f'Processing file: {os.path.basename(file_path)}')
        self._update_state("FILE_DROPPED")
        
        # Step 1: Classify the file
        agent_activity(self.name, 'CLASSIFYING', 'Classifying file')
        classification = self.file_classifier.process(file_path)
        self._update_state("CLASSIFIED")
        self.artifacts['classification'] = classification
        
        # Step 2: Profile the data
        agent_activity(self.name, 'PROFILING', 'Profiling data')
        profile = self.data_profiler.process(file_path, classification)
        self._update_state("PROFILED")
        self.artifacts['profile'] = profile
        
        # Step 3: Create data dictionary
        agent_activity(self.name, 'CREATING_DICTIONARY', 'Creating data dictionary')
        dictionary = self.dictionary_synthesizer.process(profile, classification)
        self._update_state("DICT_DRAFT")
        
        # Save dictionary to file
        timestamp = str(int(pd.Timestamp.now().timestamp()))
        dict_path = os.path.join('temp', f"{timestamp}_dict.json")
        with open(dict_path, 'w') as f:
            json.dump(dictionary, f, indent=2)
        self.artifacts['dictionary'] = dictionary
        self.artifacts['dict_path'] = dict_path
        
        # Step 4: Create database
        agent_activity(self.name, 'CREATING_DATABASE', 'Creating database')
        db_path = self._create_database(file_path, dictionary, classification, timestamp)
        self._update_state("READY")
        self.artifacts['db_path'] = db_path
        
        agent_activity(self.name, 'COMPLETED', 'File processing completed')
        
        return {
            "success": True,
            "classification": classification,
            "profile": profile,
            "dictionary": dictionary,
            "db_path": db_path,
            "dict_path": dict_path,
            "state": self.current_state
        }
    
    def _create_database(self, file_path: str, dictionary: Dict[str, Any], 
                        classification: Dict[str, Any], timestamp: str) -> str:
        """
        Create a SQLite database from the processed file.
        
        Args:
            file_path: Path to the original file
            dictionary: Data dictionary
            classification: File classification results
            timestamp: Timestamp for naming
            
        Returns:
            Path to the created database
        """
        db_path = os.path.join('temp', f"{timestamp}_database.db")
        file_type = classification.get('file_type', '').lower()
        
        try:
            # Create a connection to the database
            conn = sqlite3.connect(db_path)
            
            # Process based on file type
            if file_type == 'csv':
                df = pd.read_csv(file_path)
                table_name = os.path.splitext(os.path.basename(file_path))[0]
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            elif file_type == 'json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    table_name = os.path.splitext(os.path.basename(file_path))[0]
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
                else:
                    # Handle nested JSON
                    for key, value in data.items():
                        if isinstance(value, list):
                            df = pd.DataFrame(value)
                            df.to_sql(key, conn, if_exists='replace', index=False)
            elif file_type == 'excel':
                excel_file = pd.ExcelFile(file_path)
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    df.to_sql(sheet_name, conn, if_exists='replace', index=False)
            else:
                # For other file types, try to use pandas to read it
                try:
                    df = pd.read_csv(file_path)  # Default to CSV
                    table_name = os.path.splitext(os.path.basename(file_path))[0]
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
                except:
                    agent_activity(self.name, 'ERROR', f'Unsupported file type: {file_type}')
            
            # Save the original file to temp directory for reference
            dest_path = os.path.join('temp', f"{timestamp}_{os.path.basename(file_path)}")
            with open(file_path, 'rb') as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
            
            conn.close()
            agent_activity(self.name, 'DATABASE_CREATED', f'Database created at {db_path}')
            return db_path
            
        except Exception as e:
            agent_activity(self.name, 'ERROR', f'Error creating database: {str(e)}')
            return None
    
    def _update_state(self, new_state: str) -> None:
        """
        Update the current workflow state.
        
        Args:
            new_state: The new state to transition to
        """
        agent_activity(self.name, 'STATE_CHANGE', f'State change: {self.current_state} -> {new_state}')
        self.current_state = new_state
