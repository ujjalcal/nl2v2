# NL2SQL Tool

A minimalist, agentic AI application that converts natural language queries to SQL and processes them using GPT-4.1 Nano. This application allows users to upload data files (CSV, JSON, XML, YAML, Excel), analyze them, and query them using natural language through a clean, OpenAI-inspired chat interface.

## Features

- **Minimalist OpenAI-Style Interface**: Clean, modern UI with a simple chat-based interaction model
- **Agentic Query Processing**: Uses GPT-4.1 Nano to analyze and process queries
- **Complex Query Handling**: Breaks down complex queries into manageable sub-tasks
- **Multi-tool Execution**: Executes plans using SQL and Python as needed
- **Transparent Reasoning**: Shows the reasoning process for each query
- **File Analysis**: Automatically analyzes uploaded data files with real-time feedback
- **Cache Management**: Easily clear uploaded and generated files with a single click

## Architecture

Based on my analysis of the codebase and the user's requirements, here's a comprehensive bullet list for the NL2SQL Agentic Architecture with a focus on LLM-driven decision making:

NL2SQL Agentic Architecture: LLM-Driven Approach
Core Philosophy
LLM as the Brain: All decision logic dynamically handled by GPT-4.1 nano
Zero Hardcoded Rules: No predefined decision trees or fixed workflows
Emergent Intelligence: System develops its own patterns and strategies
Minimal Scaffolding: Just enough Python to invoke LLM and handle results
Data Processor Pipeline
FileClassifierAgent
Identifies file type, structure, and content purpose
Determines if file contains schema or actual data
Makes format-specific parsing decisions dynamically
DataProfilerAgent
Analyzes data patterns, types, and statistics
Identifies anomalies and quality issues
Suggests data cleaning approaches based on content
DictionarySynthesizerAgent
Creates schema/dictionary from profiled data
Infers relationships between tables
Generates comprehensive column descriptions
DatabaseSetupAgent
Creates and configures the database
Determines optimal table structures
Handles schema evolution for changing data
BulkLoaderAgent
Loads data into the database
Handles format-specific loading challenges
Validates data integrity during loading
Query Processor Pipeline
ConversationalAgent
Manages multi-turn conversations
Determines when follow-up questions are needed
Maintains conversation context without predefined flows
QueryNormalizerAgent
Standardizes and cleans queries
Resolves ambiguities in natural language
Expands abbreviations and domain-specific terms
QueryDecomposerAgent
Breaks down complex queries into sub-queries
Identifies query components that can be parallelized
Determines dependencies between sub-queries
ExecutionPlannerAgent
Creates execution plans for hybrid SQL/Python processing
Builds directed acyclic graphs (DAGs) of execution steps
Dynamically decides optimal execution approach for each component
SQLGeneratorAgent
Translates natural language to SQL
Handles complex joins and nested queries
Optimizes SQL for performance
SQLExecutorAgent
Executes SQL queries against the database
Handles error recovery and query optimization
Formats results for presentation
CodeGeneratorAgent
Generates Python code for complex operations
Selects appropriate libraries (pandas, matplotlib, etc.)
Creates visualizations based on query intent
CodeExecutorAgent
Executes Python code in a sandboxed environment
Captures outputs, visualizations, and results
Handles execution errors gracefully
ResultCombinerAgent
Joins results from multiple execution paths
Determines the best presentation format
Creates final visualizations and summaries
System Architecture
Workflow Orchestrator
Manages the finite-state machine (FSM) for data processing
Tracks state transitions: FILE_DROPPED → CLASSIFIED → PROFILED → DICT_DRAFT → DICT_REVIEWED → READY → BULK_LOADED → DONE
Prevents invalid state transitions
Task Scheduler
Coordinates execution of tasks based on workflow state
Manages dependencies between agents
Handles parallel execution when possible
Artifact Registry
Tracks all generated artifacts with immutable hashes
Maintains provenance of all system outputs
Enables reproducibility of results
Event-Driven Updates
Real-time agent activity tracking via Server-Sent Events (SSE)
Push-based updates to the UI
Detailed tracking of agent activities and state transitions
Implementation Guidelines
Use GPT-4.1 nano for all agent LLM tasks
Single file with multiple functions where possible
Focus on demo functionality without extensive error handling
Use "temp" folder for all uploads and generated files
Use "test" folder for test files
Regular GitHub commits for version control
UI Components
Streamlit-based interface for simplicity and rapid development
Execution plan visualization showing SQL vs Python components
Real-time agent activity display with color-coding
Interactive query refinement based on conversational context
This architecture fully embraces the agentic AI paradigm, allowing the LLM to make all decisions dynamically rather than following predefined rules, creating a flexible system that can handle a wide range of data analysis tasks.

## Setup Instructions

### Prerequisites

- Python 3.8+

### Installation

1. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On macOS/Linux
   ```

2. Install Python dependencies:
   ```
   pip install flask flask-cors pandas numpy openai python-dotenv pyyaml openpyxl xmltodict
   ```

3. Set up your OpenAI API key:
   Create a `.env` file in the root directory with the following content:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. Start the application:
   ```
   python nl2sql_app.py
   ```
   
   This will launch both the UI and API servers and open the application in your browser.

## Usage

1. Open the application in your browser (typically at http://localhost:5000)
2. Upload a data file using the paperclip attachment button in the chat input area
3. Wait for the file to be analyzed - you'll see real-time progress with animated indicators
4. Ask questions about your data in natural language
5. View the results in a clean, well-formatted table
6. Use the trash icon in the header to clear all uploaded and generated files when needed

## Folder Structure

- `temp/` - Temporary folder for uploaded files and generated data
- `test/` - Test files and examples

## Example Queries

- "What is the average loan amount by state?"
- "Show me the top 5 counties with the highest denial rates"
- "How many applicants have income greater than $100,000?"
- "What's the relationship between loan amount and income?"
- "Compare approval rates between different demographic groups"
- "Which property types have the highest average loan amounts?"

## Screenshots

![NL2SQL Chat Interface](screenshots/chat_interface.png)

## Contributing

This is a demo application focused on showcasing agentic AI capabilities. Contributions that align with keeping the codebase simple and focused on the core functionality are welcome.

## License

MIT
