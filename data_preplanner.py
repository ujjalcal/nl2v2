import os
import csv
import yaml
import json
import pandas as pd
import time
import re
from typing import Dict, List, Any, Optional
import openai
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

# Load environment variables
load_dotenv()

class DataPreplanner:
    """
    A class to analyze data files (CSV, JSON, XML, Excel) and generate enriched data dictionaries
    using GPT for field analysis.
    """
    
    def __init__(self):
        """Initialize the DataPreplanner with OpenAI client."""
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def analyze_schema(self, file_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        Analyze a schema file and generate a data dictionary directly from the schema.
        
        Args:
            file_path: Path to the schema file
            progress_callback: Optional callback function to report progress
            
        Returns:
            Dictionary containing the data dictionary derived from the schema
        """
        # Determine file type from extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Read schema file based on extension
        if file_ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        elif file_ext == '.json':
            df = pd.read_json(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported schema file format: {file_ext}")
        
        # Extract basic metadata
        dataset_name = os.path.basename(file_path).split('.')[0]
        
        # Initialize data dictionary
        data_dict = {
            "dataset_name": dataset_name,
            "fields_count": 0,  # Will be updated later
            "description": f"Schema for {dataset_name} database"
        }
        
        # Use GPT to analyze the schema structure
        prompt = f"""
        I have a schema file with the following structure. Please analyze it and help me understand the tables and columns:
        
        {df.head(20).to_string()}
        
        Please provide a detailed analysis of this schema, including:
        1. What tables are defined in this schema?
        2. What are the columns for each table?
        3. What are the data types for each column?
        4. Are there any primary keys or relationships between tables?
        
        Format your response as a JSON object with the structure that can be directly used as a data dictionary.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that specializes in database schema analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000
            )
            
            schema_analysis = response.choices[0].message.content
            
            # Try to extract JSON from the response
            try:
                # Find JSON content if wrapped in markdown code blocks
                json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', schema_analysis)
                if json_match:
                    schema_analysis = json_match.group(1)
                
                # Parse the JSON
                schema_dict = json.loads(schema_analysis)
                
                # Merge with our data dictionary
                data_dict.update(schema_dict)
            except Exception as e:
                print(f"Error parsing schema analysis: {str(e)}")
                # If JSON parsing fails, use the raw text
                data_dict["schema_analysis"] = schema_analysis
        except Exception as e:
            print(f"Error analyzing schema with GPT: {str(e)}")
            # Fallback to basic analysis
            data_dict["schema_analysis"] = "Error analyzing schema with GPT"
        
        # Process the schema directly if it has a standard structure (TABLE_NAME, COLUMN_NAME, DATA_TYPE)
        if all(col in df.columns for col in ['TABLE_NAME', 'COLUMN_NAME', 'DATA_TYPE']):
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
                    "description": f"{column_name} of type {data_type}",
                    "categorical": data_type.upper() in ["TEXT", "VARCHAR", "CHAR", "ENUM"],
                    "constraints": {},
                    "synonyms": [column_name.replace("_", " ")],
                    "relationships": []
                }
                
                # Add ordinal position if available
                if 'ORDINAL_POSITION' in df.columns:
                    column_info["ordinal_position"] = row.get('ORDINAL_POSITION')
                
                tables[table_name].append(column_info)
            
            # Add tables to data dictionary
            data_dict["tables"] = tables
            data_dict["fields_count"] = sum(len(columns) for columns in tables.values())
        
        return data_dict
        
    def analyze_data(self, file_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        Analyze a data file (CSV, JSON, XML, Excel) and generate an enriched data dictionary.
        
        Args:
            file_path: Path to the data file
            progress_callback: Optional callback function to report progress
            
        Returns:
            Dictionary containing the enriched data dictionary
        """
        # Determine file type from extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Read file based on extension
        if file_ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        elif file_ext == '.json':
            df = pd.read_json(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_ext == '.xml':
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
        
        # Extract basic metadata
        dataset_name = os.path.basename(file_path).split('.')[0]
        fields_count = len(df.columns)
        
        if progress_callback:
            progress_callback("Analyzing dataset...", 0, 3)
        
        # Initialize data dictionary
        data_dict = {
            "dataset_name": dataset_name,
            "fields_count": fields_count,
        }
        
        # Generate dataset description
        data_dict["description"] = self._generate_dataset_description(dataset_name, df)
        
        if progress_callback:
            progress_callback("Analyzing fields in bulk...", 1, 3)
        
        # Analyze fields in bulk
        field_metadata_dict = self._analyze_fields_bulk(df)
        
        # Add field metadata to data dictionary
        for column, metadata in field_metadata_dict.items():
            data_dict[column] = metadata
        
        # Identify relationships between fields
        if progress_callback:
            progress_callback("Identifying relationships between fields...", 2, 3)
        
        self._identify_relationships_bulk(data_dict, df)
        
        if progress_callback:
            progress_callback("Analysis complete!", 3, 3)
            
        return data_dict
        
    def _analyze_fields_bulk(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Analyze all fields in bulk using multiple GPT calls to handle large datasets.
        
        Args:
            df: DataFrame containing the data
            
        Returns:
            Dictionary mapping field names to their metadata
        """
        # For large datasets, process fields in batches
        all_columns = df.columns.tolist()
        batch_size = 15  # Process 15 columns at a time to avoid token limits
        field_metadata_dict = {}
        
        # Process columns in batches
        for i in range(0, len(all_columns), batch_size):
            batch_columns = all_columns[i:i+batch_size]
            
            # Prepare sample data for each field in this batch
            fields_data = {}
            for column in batch_columns:
                # Get sample values
                if len(df) > 0:
                    if len(df) >= 5:
                        non_null_values = df[column].dropna()
                        if len(non_null_values) > 0:
                            sample_values = non_null_values.sample(min(5, len(non_null_values))).tolist()
                        else:
                            sample_values = []
                    else:
                        sample_values = df[column].dropna().tolist()
                else:
                    sample_values = []
                    
                # Format sample values
                sample_str = ", ".join([str(val) for val in sample_values[:5]])
                if not sample_str:
                    sample_str = "[No non-null samples available]"
                    
                # Store field data
                fields_data[column] = {
                    "dtype": str(df[column].dtype),
                    "sample": sample_str,
                    "raw_samples": sample_values
                }
            
            # Create prompt for GPT for this batch
            fields_str = "\n".join([
                f"Field: {field}\nType: {data['dtype']}\nSample: {data['sample']}"
                for field, data in fields_data.items()
            ])
            
            prompt = f"""
            Analyze these dataset fields and provide metadata. Be concise but accurate.
            
            {fields_str}
            
            For each field, return a YAML object with these keys:
            - type: The technical data type (string, integer, float, date, etc.)
            - categorical: 'yes' if this is a categorical field, 'no' if continuous/numeric
            - description: A brief description of what this field represents
            - constraints: A string describing any constraints (IMPORTANT: always put quotes around the constraints value)
            - synonyms: A list of 2-3 alternative names for this field
            
            Format your response as a YAML document with each field name as a top-level key.
            IMPORTANT: Always put quotes around the constraints value to ensure valid YAML.
            
            Example:
            
            field_name1:
              type: string
              categorical: yes
              description: Customer's full name
              constraints: "Max length 100 characters"
              synonyms: [name, customer_name]
            
            field_name2:
              type: integer
              categorical: no
              description: Customer's age in years
              constraints: "Range 18-120"
              synonyms: [age, years]
            """
            
            # Query GPT
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes data fields and provides metadata in YAML format. Do not use markdown code blocks in your response."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000
            )
            
            # Extract the YAML content from the response
            yaml_content = response.choices[0].message.content.strip()
            
            # Try to fix common YAML issues
            yaml_content = self._sanitize_yaml(yaml_content)
            
            try:
                # Parse the YAML content
                batch_metadata = yaml.safe_load(yaml_content)
                
                # Add sample values and relationships to each field's metadata
                for column in batch_columns:
                    if column in batch_metadata:
                        # Add sample values to metadata
                        batch_metadata[column]["sample"] = fields_data[column]["raw_samples"]
                        
                        # Ensure relationships key exists
                        batch_metadata[column]["relationships"] = []
                        
                        # Add to the complete metadata dictionary
                        field_metadata_dict[column] = batch_metadata[column]
                    else:
                        print(f"Warning: Field {column} was not analyzed by GPT")
            except Exception as e:
                print(f"Error parsing YAML for batch {i//batch_size + 1}: {str(e)}")
                
                # Try to analyze each field individually if batch processing fails
                for column in batch_columns:
                    try:
                        # Analyze this field individually
                        print(f"Attempting individual analysis for field: {column}")
                        sample_values = fields_data[column]["raw_samples"]
                        field_metadata = self._analyze_field(column, sample_values, fields_data[column]["dtype"], df)
                        field_metadata_dict[column] = field_metadata
                    except Exception as field_e:
                        print(f"Error analyzing field {column}: {str(field_e)}")
                        # Use basic metadata as last resort
                        field_metadata_dict[column] = {
                            "type": fields_data[column]["dtype"],
                            "categorical": "yes" if "object" in fields_data[column]["dtype"] else "no",
                            "description": f"Field containing {fields_data[column]['dtype']} data",
                            "constraints": "Unknown",
                            "sample": fields_data[column]["raw_samples"],
                            "synonyms": [column.replace("_", " ")],
                            "relationships": []
                        }
        
        return field_metadata_dict
    
    def _identify_relationships_bulk(self, data_dict: Dict[str, Any], df: pd.DataFrame) -> None:
        """
        Identify relationships between fields using GPT with optimized input.
        
        Args:
            data_dict: Data dictionary to update
            df: DataFrame containing the data
        """
        # Get list of fields
        fields = [field for field in data_dict.keys() if field not in ["dataset_name", "description", "fields_count"]]
        
        # Use heuristic approach for relationship identification
        self._identify_relationships_heuristic(data_dict, fields)
    
    def _identify_relationships_heuristic(self, data_dict: Dict[str, Any], field_names: List[str]) -> None:
        """
        Identify relationships using heuristics instead of GPT.
        
        Args:
            data_dict: Data dictionary to update
            field_names: List of field names
        """
        for field in field_names:
            data_dict[field]["relationships"] = self._identify_relationships_for_field(field, field_names)
    
    def _identify_relationships_for_field(self, field: str, field_names: List[str]) -> List[str]:
        """
        Identify relationships for a single field using heuristics.
        
        Args:
            field: Field to find relationships for
            field_names: List of all field names
            
        Returns:
            List of related field names
        """
        relationships = []
        
        # Look for fields with similar names
        for other_field in field_names:
            if other_field != field:
                # Check if one field is contained in the other
                if field.lower() in other_field.lower() or other_field.lower() in field.lower():
                    relationships.append(other_field)
                    
                # Check for ID-name relationships
                if "id" in field.lower() and field.lower() != "id":
                    base_name = field.lower().replace("_id", "").replace("id_", "").replace("id", "")
                    if base_name and (base_name in other_field.lower() and "name" in other_field.lower()):
                        relationships.append(other_field)
                        
                # Check for date relationships
                if "date" in field.lower() and "date" in other_field.lower():
                    relationships.append(other_field)
        
        # Limit to top 3 relationships
        return list(set(relationships))[:3]
    
    def _generate_dataset_description(self, dataset_name: str, df: pd.DataFrame) -> str:
        """
        Generate a description for the dataset using GPT with optimized input.
        
        Args:
            dataset_name: Name of the dataset
            df: DataFrame containing the data
            
        Returns:
            Description of the dataset
        """
        # Get column names and sample data
        columns = df.columns.tolist()
        
        # Get a sample of the data (first 3 rows)
        sample_data = df.head(3).to_dict(orient='records')
        sample_str = json.dumps(sample_data, default=str)
        
        # Truncate if too large
        if len(sample_str) > 1000:
            sample_str = sample_str[:1000] + "...(truncated)"
        
        # Create prompt for GPT
        prompt = f"""
        Generate a concise description for this dataset.
        
        Dataset Name: {dataset_name}
        Columns: {columns}
        Sample Data: {sample_str}
        """
        
        # Get response from GPT
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes datasets and provides concise descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        
        # Extract the description from the response
        description = response.choices[0].message.content.strip()
        
        return description
        
    def _analyze_field(self, field_name: str, sample_values: List, dtype: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a field using GPT to generate enriched metadata.
        
        Args:
            field_name: Name of the field
            sample_values: List of sample values
            dtype: Data type of the field
            df: DataFrame containing the data
            
        Returns:
            Dictionary containing field metadata
        """
        # Start timer for timeout protection
        start_time = time.time()
        
        # Format sample values for the prompt
        sample_str = ", ".join([str(val) for val in sample_values[:5]])
        if not sample_str:
            sample_str = "[No non-null samples available]"
        
        # Create prompt for GPT
        prompt = f"""
        Analyze this dataset field and provide metadata in YAML format. Be concise but accurate.
        
        Field name: {field_name}
        Data type: {dtype}
        Sample values: {sample_str}
        
        Return ONLY a YAML object with these keys:
        - type: The technical data type (string, integer, float, date, etc.)
        - categorical: 'yes' if this is a categorical field, 'no' if continuous/numeric
        - description: A brief description of what this field represents
        - constraints: Any constraints on the values (e.g., "Range: 0-100", "Valid values: A, B, C", "Format: YYYY-MM-DD")
        - synonyms: A list of 2-3 alternative names for this field
        
        Example response:
        type: string
        categorical: yes
        description: Customer's full name including first and last name
        constraints: Max length 100 characters
        synonyms: [full_name, customer_name, client_name]
        """
        
        # Get response from GPT
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",  # Using GPT-4.1 Nano for larger context window
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes data fields and provides metadata in YAML format. Do not use markdown code blocks in your response."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400
        )
        
        # Extract the YAML content from the response
        yaml_content = response.choices[0].message.content.strip()
        
        # Parse the YAML content
        field_metadata = yaml.safe_load(yaml_content)
        
        # Ensure all required keys are present
        required_keys = ["type", "categorical", "description", "constraints", "synonyms"]
        for key in required_keys:
            if key not in field_metadata:
                field_metadata[key] = "Unknown" if key != "synonyms" else [field_name.replace("_", " ")]
        
        # Ensure sample values are included
        field_metadata["sample"] = sample_values[:5] if len(sample_values) > 5 else sample_values
        
        # Try to identify relationships with other fields (with timeout protection)
        if time.time() - start_time < 12:  # Only do this if we have time
            field_metadata["relationships"] = []  # Will be filled in by bulk relationship analysis
        else:
            field_metadata["relationships"] = []
        
        return field_metadata
    
    def _sanitize_yaml(self, yaml_content: str) -> str:
        """
        Sanitize YAML content to fix common issues that cause parsing errors.
        
        Args:
            yaml_content: The YAML content to sanitize
            
        Returns:
            Sanitized YAML content
        """
        # Remove markdown code block markers if present
        yaml_content = re.sub(r'^```yaml\s*', '', yaml_content)
        yaml_content = re.sub(r'^```yml\s*', '', yaml_content)
        yaml_content = re.sub(r'\s*```$', '', yaml_content)
        
        # Fix lines with unquoted values containing colons
        lines = yaml_content.split('\n')
        sanitized_lines = []
        
        for line in lines:
            # Skip empty lines or lines without content
            if not line.strip() or ':' not in line:
                sanitized_lines.append(line)
                continue
                
            # Check if this is a line with a key-value pair
            if ':' in line and not line.strip().startswith('-'):
                key_part, value_part = line.split(':', 1)
                
                # If the value contains a colon and is not already quoted, quote it
                if ':' in value_part and not (value_part.strip().startswith('"') and value_part.strip().endswith('"')):
                    sanitized_line = f"{key_part}: \"{value_part.strip()}\""
                    sanitized_lines.append(sanitized_line)
                else:
                    sanitized_lines.append(line)
            else:
                sanitized_lines.append(line)
        
        return '\n'.join(sanitized_lines)
    
    def save_data_dictionary(self, data_dict: Dict[str, Any], output_path: str, format: str = "yaml") -> None:
        """
        Save the data dictionary to a file.
        
        Args:
            data_dict: The data dictionary to save
            output_path: Path to save the file
            format: Format to save the file in ('yaml' or 'json')
        """
        if format.lower() == "yaml":
            with open(output_path, 'w') as f:
                yaml.dump(data_dict, f, sort_keys=False)
        elif format.lower() == "json":
            with open(output_path, 'w') as f:
                json.dump(data_dict, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

# Example usage
if __name__ == "__main__":
    analyzer = DataPreplanner()
    
    # Analyze data file (supports CSV, JSON, XML, Excel)
    data_dict = analyzer.analyze_data("path/to/your/file.csv")
    
    # Save data dictionary
    analyzer.save_data_dictionary(data_dict, "data_dictionary.yaml")
    
    # Print summary
    print(f"Analyzed dataset: {data_dict['dataset_name']}")
    print(f"Description: {data_dict['description']}")
    print(f"Number of fields: {data_dict['fields_count']}")
    print("Fields:")
    for field in data_dict:
        if field not in ["dataset_name", "description", "fields_count"]:
            print(f"  - {field}: {data_dict[field]['description']}")

    # Examples for different file formats:
    # data_dict = analyzer.analyze_data("path/to/your/file.json")
    # data_dict = analyzer.analyze_data("path/to/your/file.xml")
    # data_dict = analyzer.analyze_data("path/to/your/file.xlsx")
