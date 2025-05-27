# NL2SQL Tool

An agentic AI application that converts natural language queries to SQL and processes them using GPT-4.1 Nano. This application allows users to upload data files (CSV, JSON, XML, Excel), analyze them, and query them using natural language.

## Features

- **Agentic Query Processing**: Uses GPT-4.1 Nano to analyze and process queries
- **Complex Query Handling**: Breaks down complex queries into manageable sub-tasks
- **Multi-tool Execution**: Executes plans using SQL and Python as needed
- **Transparent Reasoning**: Shows the reasoning process for each query
- **File Analysis**: Automatically analyzes uploaded data files

## Architecture

The application uses a React frontend with a Flask backend:

- **Frontend**: React-based chat interface with file upload capabilities
- **Backend**: Flask API providing endpoints for message processing, file uploads, and data access

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn

### Backend Setup

1. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

2. Install Python dependencies:
   ```
   pip install flask flask-cors pandas openai python-dotenv pyyaml
   ```

3. Set up your OpenAI API key:
   Create a `.env` file in the root directory with the following content:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. Start the Flask backend:
   ```
   python api.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```

4. For production build:
   ```
   npm run build
   ```

## Usage

1. Open the application in your browser (typically at http://localhost:3000)
2. Upload a data file using the attachment button in the chat interface
3. Wait for the file to be analyzed
4. Ask questions about your data in natural language
5. View the results, reasoning process, and execution details

## Example Queries

- "What is the average value by category?"
- "Show me the top 5 items by price"
- "Which products have been sold more than 100 times?"
- "Calculate the median price for each category"
- "Compare sales between regions"
