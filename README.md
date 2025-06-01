# NL2SQL Tool

A minimalist, agentic AI application that converts natural language queries to SQL and processes them using GPT-4.1 Nano. This application allows users to upload data files (CSV, JSON, XML, YAML, Excel), analyze them, and query them using natural language through a clean, chat-based interface.

## Features

- **Agentic Architecture**: Specialized agents work together to process queries and data
- **Real-time Agent Activity**: Server-Sent Events (SSE) for live updates on agent activities
- **Comprehensive Data Processing**: Automatic file classification, profiling, and dictionary creation
- **Natural Language Queries**: Convert plain English questions to optimized SQL
- **Complex Query Handling**: Breaks down complex queries into manageable sub-tasks
- **Robust Error Handling**: Comprehensive error recovery and fallback mechanisms
- **Workflow State Management**: Clear state transitions with validation

## Agentic Architecture

The NL2SQL tool is built on a true agentic architecture with specialized agents that handle different aspects of the workflow:

### Core Components

- **Workflow Orchestrator**: Manages the finite-state machine (FSM) for data processing
- **Task Scheduler**: Coordinates execution of tasks based on workflow state
- **Artifact Registry**: Tracks all artifacts with immutable hashes
- **Event System**: Real-time agent activity tracking via Server-Sent Events (SSE)

### Specialized Agents

- **FileClassifierAgent**: Identifies file type, structure, and content purpose
- **DataProfilerAgent**: Analyzes data patterns, types, and statistics
- **DictionarySynthesizerAgent**: Creates schema/dictionary from profiled data
- **QueryNormalizerAgent**: Standardizes and cleans queries
- **QueryDecomposerAgent**: Breaks down complex queries into sub-queries
- **SQLGeneratorAgent**: Translates natural language to SQL
- **SQLExecutorAgent**: Executes SQL queries against the database
- **ResultCombinerAgent**: Joins results from multiple execution paths

### Workflow States

The system implements a complete finite-state machine with the following states:
```
FILE_DROPPED → CLASSIFIED → PROFILED → DICT_DRAFT → DICT_REVIEWED → READY → BULK_LOADED → DONE
```

Each state transition is validated to prevent hallucinations and ensure data integrity.

## Query Pipeline

The QueryPipeline class provides a modular approach to processing natural language queries:

1. **Query Analysis**: Determines query intent, complexity, and processing needs
2. **Query Normalization**: Standardizes terminology to match database schema
3. **SQL Conversion**: Transforms natural language to optimized SQL
4. **Query Execution**: Runs the SQL against the database
5. **Result Formatting**: Presents results in a clean, readable format

## Setup Instructions

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On macOS/Linux
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
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
   
   This will launch both the API server and UI.

## Usage

1. Upload a data file (CSV, JSON, XML, YAML, Excel)
2. Watch as the agents classify, profile, and create a data dictionary
3. Ask questions about your data in natural language
4. View the results and explanations
5. Use the clear cache option to remove uploaded and generated files when needed

## Folder Structure

- `temp/` - Temporary folder for uploaded files and generated data
- `test/` - Test files and examples

## Example Queries

- "What is the average value by category?"
- "Show me the top 5 items with the highest prices"
- "How many records are in each table?"
- "What's the relationship between price and quantity?"
- "Compare values across different categories"
- "Generate sample questions for this database"

## Implementation Notes

- Uses GPT-4.1 Nano for all LLM tasks
- Focuses on demo functionality without excessive error handling
- Keeps code simple with single files containing multiple functions where possible
- Follows anti-hallucination backbone design with state validation

## License

MIT