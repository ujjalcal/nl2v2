# NL2SQL Tool

A minimalist, agentic AI application that converts natural language queries to SQL and processes them using GPT-4.1 Nano. This application allows users to upload data files (CSV, JSON, XML, YAML, Excel), analyze them, and query them using natural language through a clean, chat-based interface.

## Features

- **Agentic Architecture**: Specialized agents work together to process queries and data
- **Real-time Agent Activity**: Server-Sent Events (SSE) for live updates on agent activities
- **Data Processing**: Automatic file classification, profiling, and dictionary creation
- **Natural Language Queries**: Convert plain English questions to optimized SQL
- **Multi-format Support**: CSV, JSON, XML, YAML, and Excel files

## Agentic Architecture

The NL2SQL tool is built on an agentic architecture with specialized agents that handle different aspects of the workflow:

### Core Agents

- **FileClassifierAgent**: Identifies file type, structure, and content purpose
- **DataProfilerAgent**: Analyzes data patterns, types, and statistics
- **DictionarySynthesizerAgent**: Creates schema/dictionary from profiled data
- **QueryNormalizerAgent**: Standardizes and cleans queries
- **QueryDecomposerAgent**: Breaks down complex queries into sub-queries
- **SQLGeneratorAgent**: Translates natural language to SQL
- **SQLExecutorAgent**: Executes SQL queries against the database
- **CodeGeneratorAgent**: Generates Python code for complex operations
- **CodeExecutorAgent**: Executes generated Python code in a sandboxed environment
- **ResultCombinerAgent**: Joins results from multiple execution paths

### Workflow States

The system implements a state machine with the following states:
```
IDLE → PROCESSING → FILE_DROPPED → CLASSIFIED → PROFILED → DICT_DRAFT → DICT_REVIEWED → READY → BULK_LOADED → DONE
```

## API Endpoints

- `POST /api/upload`: Upload and process a data file
  - Accepts: multipart/form-data with 'file' field
  - Returns: Processing status and file information

- `POST /api/query`: Process a natural language query
  - Accepts: JSON with 'query' field
  - Returns: Query results and execution details

- `GET /api/events`: Stream real-time agent activities
  - Returns: Server-Sent Events stream

- `GET /api/health`: Health check endpoint
  - Returns: API status

## Setup Instructions

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On macOS/Linux
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   
   Required packages:
   - python-dotenv
   - openai
   - pyyaml
   - flask
   - flask-cors
   - pandas
   - werkzeug
   - matplotlib
   - numpy
   - xmltodict
   - openpyxl (for Excel support)

3. Configure your OpenAI API key in a `.env` file:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. Start the application:
   ```
   python nl2sql_app.py
   ```
   
   This will start:
   - API server at http://localhost:5000
   - Web UI at http://localhost:5001

## Configuration

Environment variables:
- `OPENAI_API_KEY`: Required. Your OpenAI API key
- `TEMPORARY_DIR`: Directory for temporary files (default: 'temp')
- `UPLOAD_FOLDER`: Directory for uploaded files (default: 'uploads')
- `MAX_CONTENT_LENGTH`: Maximum file upload size in bytes (default: 16MB)

## Usage

1. Upload a data file using the web interface or API
2. The system will automatically process the file through the agent pipeline
3. Ask questions about your data using natural language
4. View the results and SQL queries in the web interface

## File Structure

- `/temp`: Temporary files and processing artifacts
- `/test`: Test files and examples
- `/uploads`: Default location for uploaded files

## License

MIT