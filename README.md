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

The application uses a single-file Flask application:

- **Frontend**: Minimalist HTML/CSS/JS chat interface with file upload capabilities
- **Backend**: Flask API providing endpoints for message processing, file uploads, and data access

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
   python minimalist_api.py
   ```

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
