import os
import csv
import yaml
import json
import pandas as pd
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
        """Initialize the CSVPreplanner with OpenAI client."""
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
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
        try:
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
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
        except Exception as e:
            raise Exception(f"Error reading file {file_path}: {str(e)}")
        
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
        try:
            data_dict["description"] = self._generate_dataset_description(dataset_name, df)
        except Exception as e:
            data_dict["description"] = f"Dataset containing {fields_count} fields and {len(df)} records."
            print(f"Error generating dataset description: {str(e)}")
        
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
        
        try:
            self._identify_relationships_bulk(data_dict, df)
        except Exception as e:
            print(f"Error identifying relationships: {str(e)}")
        
        if progress_callback:
            progress_callback("Analysis complete!", 3, 3)
            
        return data_dict
        
    def _analyze_fields_bulk(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Analyze all fields in bulk using a single GPT call with optimized sample data.
        
        Args:
            df: DataFrame containing the data
            
        Returns:
            Dictionary mapping field names to their metadata
        """
        # Get basic dataframe info
        row_count = len(df)
        col_count = len(df.columns)
        
        # Prepare field information with minimal but representative samples
        field_info = []
        for column in df.columns:
            # Get sample values (limited to 2-3 per field)
            sample_values = []
            if row_count > 0:
                try:
                    non_null_values = df[column].dropna()
                    if len(non_null_values) > 0:
                        # For categorical fields with few unique values, show all unique values (up to 3)
                        unique_vals = non_null_values.unique()
                        if len(unique_vals) <= 3:
                            sample_values = unique_vals[:3].tolist()
                        else:
                            # Otherwise just take first 2 values
                            sample_values = non_null_values.iloc[:2].tolist()
                except Exception as e:
                    # Fallback to first value if error
                    try:
                        sample_values = [df[column].iloc[0]]
                    except:
                        pass
            
            # Convert sample values to strings and limit length
            str_samples = []
            for val in sample_values:
                str_val = str(val)
                if len(str_val) > 50:  # Truncate very long values
                    str_val = str_val[:50] + "..."
                str_samples.append(str_val)
            
            # Detect data type
            dtype = str(df[column].dtype)
            
            # Determine category
            category = "text"  # default
            if pd.api.types.is_numeric_dtype(df[column]):
                category = "continuous"
            elif pd.api.types.is_datetime64_dtype(df[column]):
                category = "temporal"
            else:
                # Check if categorical
                try:
                    unique_count = df[column].nunique()
                    if unique_count <= 10 or (unique_count / len(df) < 0.05 and unique_count <= 50):
                        category = "categorical"
                except:
                    pass
            
            field_info.append({
                "name": column,
                "type": dtype,
                "category": category,
                "sample": str_samples
            })
        
        # Create prompt for GPT - more concise than before
        prompt = f"""
        Analyze these dataset fields and provide metadata. Be concise but accurate.
        
        Fields:
        {yaml.dumps(field_info, indent=2)}
        
        For each field, provide in yaml format:
        1. type: Data type (integer, float, string, date, etc.)
        2. categorical: "yes" if the field is categorical, "no" if not
        3. description: Brief description of what this field represents
        4. constraints: Specific constraints or validation rules that should apply to this field. 
           For example:
           - For ID fields: "Primary key" or "Unique identifier"
           - For numeric fields: "Range: min-max" or "Positive values only"
           - For categorical fields: "Valid values: X, Y, Z"
           - For date fields: "Format: YYYY-MM-DD" or "Must be after 2000-01-01"
           - For text fields: "Max length: X characters" or "No special characters"
        5. synonyms: 2-3 alternative names
        6. source: Likely source of this data
        7. quality_notes: Brief notes about data quality
        
        Return a yaml object with field names as keys.
        """
        
        # Query GPT with a shorter timeout
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a data analyst that creates concise, accurate field metadata."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "yaml_object"},
                max_tokens=4000,
                timeout=20  # Shorter timeout
            )
            
            # Parse response
            field_metadata = yaml.loads(response.choices[0].message.content)
            
            # Process the response
            result = {}
            for column in df.columns:
                if column in field_metadata:
                    metadata = field_metadata[column]
                    
                    # Get actual sample values for this field (up to 3)
                    sample_values = []
                    if row_count > 0:
                        try:
                            non_null_values = df[column].dropna()
                            if len(non_null_values) > 0:
                                sample_values = non_null_values.iloc[:3].tolist()
                        except:
                            pass
                    
                    # Ensure all required fields are present
                    metadata["sample"] = sample_values
                    metadata["relationships"] = []  # Will be filled in later
                    
                    result[column] = metadata
                else:
                    # Create basic metadata for missing fields
                    dtype = str(df[column].dtype)
                    result[column] = {
                        "type": dtype,
                        "categorical": "no" if pd.api.types.is_numeric_dtype(df[column]) else "yes",
                        "description": f"Field containing {dtype} data",
                        "constraints": "Unknown",
                        "sample": sample_values if 'sample_values' in locals() else [],
                        "synonyms": [column.replace("_", " ")],
                        "relationships": []
                    }
            
            return result
            
        except Exception as e:
            print(f"Error in GPT field analysis: {str(e)}")
            # Fallback to basic metadata if GPT fails
            result = {}
            for column in df.columns:
                # Get sample values
                sample_values = []
                if row_count > 0:
                    try:
                        non_null_values = df[column].dropna()
                        if len(non_null_values) > 0:
                            sample_values = non_null_values.iloc[:3].tolist()
                    except:
                        pass
                
                # Determine basic type and category
                dtype = str(df[column].dtype)
                if pd.api.types.is_numeric_dtype(df[column]):
                    category = "continuous"
                    inferred_type = "number"
                elif pd.api.types.is_datetime64_dtype(df[column]):
                    category = "temporal"
                    inferred_type = "date"
                else:
                    category = "text"
                    inferred_type = "string"
                
                # Create basic metadata
                result[column] = {
                    "type": inferred_type,
                    "categorical": "no" if category == "continuous" else "yes",
                    "description": f"Contains data for {column.replace('_', ' ')}",
                    "constraints": "Unknown",
                    "sample": sample_values,
                    "synonyms": [column.replace("_", " ")],
                    "relationships": []
                }
            
            return result
    
    def _identify_relationships_bulk(self, data_dict: Dict[str, Any], df: pd.DataFrame) -> None:
        """
        Identify relationships between fields using GPT with optimized input.
        
        Args:
            data_dict: Data dictionary to update
            df: DataFrame containing the data
        """
        # Create a list of all field names (excluding metadata fields)
        field_names = [f for f in data_dict.keys() if f not in ["dataset_name", "description", "fields_count"]]
        
        # If there are too many fields, use heuristics instead
        if len(field_names) > 50:  # For very large datasets, use heuristics
            self._identify_relationships_heuristic(data_dict, field_names)
            return
        
        # Create minimal field descriptions for context
        field_info = {}
        for field in field_names:
            # Get just the essential info
            field_info[field] = {
                "description": data_dict[field].get("description", ""),
                "type": data_dict[field].get("type", "")
            }
        
        # Create prompt for GPT - more concise than before
        prompt = f"""
        Identify relationships between these fields. Be concise and focus on the most important relationships.
        
        Fields:
        {yaml.dumps(field_info, indent=2)}
        
        For each field, identify up to 3 other fields that are most likely related to it.
        Consider naming patterns, semantic relationships, and potential foreign key relationships.
        
        Return a yaml object where each key is a field name and the value is an array of related field names.
        Only include meaningful relationships.
        """
        
        try:
            # Query GPT with a shorter timeout
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a data analyst that identifies relationships between database fields."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "yaml_object"},
                max_tokens=2000,
                timeout=15  # Shorter timeout
            )
            
            # Parse response
            relationships = yaml.loads(response.choices[0].message.content)
            
            # Update data dictionary with relationships
            for field in field_names:
                if field in relationships and isinstance(relationships[field], list):
                    # Filter out invalid field names
                    valid_relations = [r for r in relationships[field] if r in field_names and r != field]
                    data_dict[field]["relationships"] = valid_relations[:3]  # Limit to top 3
                else:
                    # Fallback to heuristic detection for this field
                    data_dict[field]["relationships"] = self._identify_relationships_for_field(field, field_names)
        
        except Exception as e:
            print(f"Error identifying relationships in bulk: {str(e)}")
            # Fallback to heuristic relationship detection
            self._identify_relationships_heuristic(data_dict, field_names)
    
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
        
        # Name-based relationships (common prefixes/suffixes)
        field_lower = field.lower()
        for other_field in field_names:
            if other_field != field:
                other_lower = other_field.lower()
                
                # Check for common prefixes (e.g., customer_id and customer_name)
                parts1 = field_lower.split('_')
                parts2 = other_lower.split('_')
                
                # If they share a prefix or one contains the other
                if (len(parts1) > 0 and len(parts2) > 0 and parts1[0] == parts2[0]) or \
                   (field_lower in other_lower or other_lower in field_lower):
                    relationships.append(other_field)
        
        # Type-based relationships (e.g., id fields often relate to each other)
        if 'id' in field_lower or field_lower.endswith('_id'):
            for other_field in field_names:
                if other_field != field and ('id' not in other_field.lower()) and len(relationships) < 3:
                    # Non-ID fields might relate to ID fields
                    if any(part in other_field.lower() for part in field_lower.split('_') if len(part) > 2):
                        relationships.append(other_field)
        
        # Limit to top 3 relationships
        return relationships[:3]
    
    def _generate_dataset_description(self, dataset_name: str, df: pd.DataFrame) -> str:
        """Generate a description for the dataset using GPT with optimized input."""
        # Get basic dataset stats
        num_rows = len(df)
        num_cols = len(df.columns)
        
        # Count data types
        numeric_cols = sum(1 for col in df.columns if pd.api.types.is_numeric_dtype(df[col]))
        datetime_cols = sum(1 for col in df.columns if pd.api.types.is_datetime64_dtype(df[col]))
        categorical_cols = 0
        for col in df.columns:
            try:
                if df[col].nunique() <= 10:
                    categorical_cols += 1
            except:
                pass
        text_cols = num_cols - numeric_cols - datetime_cols - categorical_cols
        
        # Get a sample of column names (up to 20)
        sample_columns = df.columns[:20].tolist()
        
        # Create prompt for GPT
        prompt = f"""
        Generate a concise description (1-2 sentences) for a dataset with these characteristics:
        
        Dataset name: {dataset_name}
        Number of records: {num_rows}
        Number of columns: {num_cols}
        Column types: {numeric_cols} numeric, {datetime_cols} date/time, {categorical_cols} categorical, {text_cols} text
        Sample columns: {', '.join(sample_columns)}{' (and more)' if len(df.columns) > 20 else ''}
        
        Describe what kind of data this likely contains and its potential purpose.
        """
        
        try:
            # Query GPT with a short timeout
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": "You are a data analyst assistant that creates concise dataset descriptions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                timeout=10
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating dataset description: {str(e)}")
            # Fallback to basic description
            name_parts = dataset_name.replace('_', ' ').replace('-', ' ').title()
            return f"{name_parts} dataset containing {num_rows} records with {num_cols} fields. Includes {numeric_cols} numeric fields, {datetime_cols} date/time fields, {categorical_cols} categorical fields, and {text_cols} text fields."
    
    def _analyze_field(self, field_name: str, sample_values: List, dtype: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a field using GPT to generate enriched metadata.
        
        Args:
            field_name: Name of the field
            sample_values: List of sample values
            dtype: Data type of the field
            df: DataFrame containing the data
            
        Returns:
    sample_str = ", ".join([str(val) for val in sample_values[:5]])
    if not sample_str:
        sample_str = "[No non-null samples available]"
    
    # Create a prompt that asks for specific metadata
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
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a data analyst that specializes in analyzing dataset fields and providing metadata."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=300
    )
    
    # Extract the YAML content from the response
    yaml_content = response.choices[0].message.content.strip()
        """
        relationships = []
        
        # Look for fields with similar names
        for col in df.columns:
            if col != field_name:
                if field_name in col or col in field_name:
                    relationships.append(col)
        
        # For ID fields, look for corresponding name fields
        if "id" in field_name.lower() and field_name.lower() != "id":
            base_name = field_name.lower().replace("_id", "").replace("id_", "").replace("id", "")
            for col in df.columns:
                if base_name in col.lower() and "name" in col.lower():
                    relationships.append(col)
        
        return relationships[:3]  # Limit to top 3 relationships
    
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
            import json
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
