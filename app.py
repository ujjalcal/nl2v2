import os
import json
import yaml
import streamlit as st
import pandas as pd
from data_preplanner import DataPreplanner
from agentic_processor import AgenticQueryProcessor

# Set page configuration
st.set_page_config(
    page_title="NL2SQL Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'data_dict_path' not in st.session_state:
    st.session_state.data_dict_path = None
if 'db_path' not in st.session_state:
    st.session_state.db_path = "csv_database.db"
if 'processor' not in st.session_state:
    st.session_state.processor = None

def main():
    """Main function to run the Streamlit application."""
    
    # Sidebar navigation
    st.sidebar.title("NL2SQL Tool")
    page = st.sidebar.radio("Navigation", ["Schema Analyzer", "NL2SQL", "Data Preplanning", "Agentic Query Processor"])
    
    if page == "Schema Analyzer":
        render_schema_analyzer_tab()
    elif page == "NL2SQL":
        render_nl2sql_tab()
    elif page == "Data Preplanning":
        render_csv_preplanning_tab()
    elif page == "Agentic Query Processor":
        render_agentic_processor_tab()

def render_schema_analyzer_tab():
    """Render the Schema Analyzer tab."""
    st.header("Schema Analyzer")
    st.write("Upload and analyze database schemas.")
    # Placeholder for schema analyzer functionality
    st.info("Schema analyzer functionality will be implemented here.")

def render_nl2sql_tab():
    """Render the NL2SQL tab."""
    st.header("Natural Language to SQL")
    st.write("Convert natural language queries to SQL and execute them.")
    # Placeholder for NL2SQL functionality
    st.info("NL2SQL functionality will be implemented here.")

def render_csv_preplanning_tab():
    """Render the Data Preplanning tab."""
    st.header("Data Preplanning")
    st.write("Analyze data files (CSV, JSON, XML, Excel) and generate enriched data dictionaries.")
    
    uploaded_file = st.file_uploader("Upload Data File", type=["csv", "json", "xml", "xlsx", "xls"])
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        temp_file_path = f"temp_{uploaded_file.name}"
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Show file preview based on file type
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        try:
            if file_ext == '.csv':
                df = pd.read_csv(temp_file_path, encoding='utf-8', on_bad_lines='skip')
            elif file_ext == '.json':
                df = pd.read_json(temp_file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(temp_file_path)
            elif file_ext == '.xml':
                import xml.etree.ElementTree as ET
                # Parse XML to DataFrame
                tree = ET.parse(temp_file_path)
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
                st.error(f"Unsupported file format: {file_ext}")
                return
                
            st.subheader("File Preview")
            st.dataframe(df.head(5))
            
            # Display basic stats
            st.subheader("Basic Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("Data Types", len(df.dtypes.unique()))
            
            # Analyze button
            if st.button("Analyze Data"):
                # Process data file
                analyzer = DataPreplanner()
                
                # Create a progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Define progress callback
                def update_progress(message, current, total):
                    progress_bar.progress(current / total)
                    status_text.text(message)
                
                try:
                    # Process data file with progress tracking
                    data_dict = analyzer.analyze_data(temp_file_path, progress_callback=update_progress)
                    progress_bar.progress(1.0)
                    status_text.text("Analysis complete!")
                except Exception as e:
                    st.error(f"Error analyzing file: {str(e)}")
                    return
                
                # Display results
                st.success("Data Analysis Complete!")
                
                # Show data dictionary
                st.subheader("Data Dictionary")
                st.write(f"**Dataset Name:** {data_dict['dataset_name']}")
                st.write(f"**Description:** {data_dict['description']}")
                st.write(f"**Fields Count:** {data_dict['fields_count']}")
                
                # Display fields in expandable sections
                for field_name in data_dict:
                    if field_name not in ["dataset_name", "description", "fields_count"]:
                        field_data = data_dict[field_name]
                        with st.expander(f"{field_name} ({field_data['type']})"):
                            # Handle both old and new format fields
                            if 'categorical' in field_data:
                                st.write(f"**Categorical:** {field_data['categorical']}")
                            elif 'category' in field_data:
                                st.write(f"**Category:** {field_data['category']}")
                                
                            st.write(f"**Description:** {field_data['description']}")
                            st.write(f"**Constraints:** {field_data['constraints']}")
                            st.write("**Sample Values:**")
                            st.write(field_data['sample'])
                            st.write("**Synonyms:**")
                            st.write(field_data['synonyms'])
                            
                            # Optional fields that might not be present in new format
                            if 'source' in field_data:
                                st.write(f"**Source:** {field_data['source']}")
                            if 'quality_notes' in field_data:
                                st.write(f"**Quality Notes:** {field_data['quality_notes']}")
                                
                            if field_data['relationships']:
                                st.write("**Relationships:**")
                                st.write(field_data['relationships'])
                
                # Save data dictionary for later use
                dict_path = f"data_dictionary_{data_dict['dataset_name']}.yaml"
                with open(dict_path, 'w') as f:
                    yaml.dump(data_dict, f, sort_keys=False)
                st.session_state.data_dict_path = dict_path
                
                # Option to download data dictionary
                col1, col2 = st.columns(2)
                with col1:
                    # JSON option for compatibility
                    json_data = json.dumps(data_dict, indent=2)
                    st.download_button(
                        "Download Data Dictionary (JSON)",
                        data=json_data,
                        file_name=f"data_dictionary_{data_dict['dataset_name']}.json",
                        mime="application/json"
                    )
                
                with col2:
                    # Also provide YAML download option
                    yaml_data = yaml.dump(data_dict, sort_keys=False)
                    st.download_button(
                        "Download Data Dictionary (YAML)",
                        data=yaml_data,
                        file_name=f"data_dictionary_{data_dict['dataset_name']}.yaml",
                        mime="text/yaml"
                    )
                
                # Clean up temporary file
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")
            try:
                os.remove(temp_file_path)
            except:
                pass

def render_agentic_processor_tab():
    """Render the Agentic Query Processor tab."""
    st.header("Agentic Query Processor")
    st.write("Process complex queries using an agentic approach that breaks down problems into manageable steps.")
    
    # Configuration section
    st.subheader("Configuration")
    col1, col2 = st.columns(2)
    
    with col1:
        # Data dictionary selection
        st.write("**Data Dictionary**")
        if st.session_state.data_dict_path:
            st.success(f"Using data dictionary: {os.path.basename(st.session_state.data_dict_path)}")
            if st.button("Clear Data Dictionary"):
                st.session_state.data_dict_path = None
                st.session_state.processor = None
                st.experimental_rerun()
        else:
            st.warning("No data dictionary loaded. Generate one in the CSV Preplanning tab first.")
            
            # Option to upload a data dictionary
            uploaded_dict = st.file_uploader("Or upload a data dictionary file", type=["json", "yaml", "yml"])
            if uploaded_dict:
                file_extension = uploaded_dict.name.split('.')[-1].lower()
                dict_path = f"uploaded_data_dictionary.{file_extension}"
                with open(dict_path, 'wb') as f:
                    f.write(uploaded_dict.getbuffer())
                st.session_state.data_dict_path = dict_path
                st.success(f"Data dictionary loaded successfully from {uploaded_dict.name}!")
    
    with col2:
        # Database selection
        st.write("**Database Connection**")
        db_path = st.text_input("Database Path", value=st.session_state.db_path)
        if db_path != st.session_state.db_path:
            st.session_state.db_path = db_path
            st.session_state.processor = None
    
    # Initialize processor if needed
    if st.session_state.data_dict_path and st.session_state.db_path and not st.session_state.processor:
        try:
            st.session_state.processor = AgenticQueryProcessor(
                data_dict_path=st.session_state.data_dict_path,
                db_path=st.session_state.db_path
            )
            st.success("Agentic query processor initialized successfully!")
        except Exception as e:
            st.error(f"Error initializing processor: {str(e)}")
    
    # Query processing section
    st.subheader("Query Processing")
    
    # Query input
    query = st.text_area("Enter your query", height=100, 
                         placeholder="Example: What is the average value by category?")
    
    # Process button
    if query and st.button("Process Query"):
        if not st.session_state.processor:
            st.error("Please configure the processor first by loading a data dictionary and setting a database path.")
        else:
            with st.spinner("Processing query... This may take a few moments."):
                try:
                    result = st.session_state.processor.process_query(query)
                    
                    # Display results
                    st.success("Query processed successfully!")
                    
                    # Summary
                    st.subheader("Summary")
                    st.write(result["summary"])
                    
                    # Query details
                    with st.expander("Query Details"):
                        st.write(f"**Query:** {result['query']}")
                        st.write(f"**Complexity:** {result.get('complexity', 'Unknown')}")
                        st.write(f"**Type:** {result.get('type', 'Unknown')}")
                    
                    # Reasoning steps
                    with st.expander("Reasoning Process"):
                        for step in result["reasoning_steps"]:
                            st.write(f"**{step['step_number']}. {step['step_name']}**")
                            st.write(f"{step['description']}")
                            st.write("---")
                    
                    # Execution plan
                    with st.expander("Execution Plan"):
                        for step in result["execution_plan"]:
                            st.write(f"**Step {step['step']}**")
                            st.write(f"Action: {step['action']}")
                            if "description" in step:
                                st.write(f"Description: {step['description']}")
                            if "query" in step:
                                st.code(step["query"], language="sql")
                            if "code" in step:
                                st.code(step["code"], language="python")
                            st.write("---")
                    
                    # Results
                    st.subheader("Results")
                    if isinstance(result["results"], pd.DataFrame):
                        st.dataframe(result["results"])
                    elif isinstance(result["results"], list) and len(result["results"]) > 0:
                        if all(isinstance(item, dict) for item in result["results"]):
                            # Convert list of dicts to DataFrame
                            st.dataframe(pd.DataFrame(result["results"]))
                        else:
                            st.write(result["results"])
                    else:
                        st.write(result["results"])
                    
                except Exception as e:
                    st.error(f"Error processing query: {str(e)}")

if __name__ == "__main__":
    main()
