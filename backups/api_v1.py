import os
import json
import pandas as pd
import numpy as np
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from data_preplanner import DataPreplanner
from agentic_processor import AgenticQueryProcessor

# Custom JSON encoder to handle NaN values
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Series):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super(NpEncoder, self).default(obj)

# Initialize Flask app
app = Flask(__name__, static_folder='frontend/build')
# Enable CORS with specific settings
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Ensure the data dictionary folder exists
DATA_DICT_FOLDER = 'data_dictionaries'
if not os.path.exists(DATA_DICT_FOLDER):
    os.makedirs(DATA_DICT_FOLDER)

# Global processor instance
processor = None

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads and process them"""
    if 'file' not in request.files:
        response = json.dumps({'error': 'No file part'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    file = request.files['file']
    if file.filename == '':
        response = json.dumps({'error': 'No selected file'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    # Create upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # Save the uploaded file
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    # Get file extension
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Preview data based on file type
    try:
        if file_ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        elif file_ext == '.json':
            df = pd.read_json(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_ext == '.xml':
            import xml.etree.ElementTree as ET
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
            response = json.dumps({'error': f'Unsupported file format: {file_ext}'}, cls=NpEncoder)
            return response, 400, {'Content-Type': 'application/json'}
        
        # Replace NaN values with None in the DataFrame
        df = df.replace({np.nan: None})
        
        # Get basic stats
        stats = {
            'rows': int(len(df)),
            'columns': int(len(df.columns)),
            'data_types': int(len(df.dtypes.unique())),
            'preview': df.head(5).to_dict(orient='records')
        }
        
        # Use custom JSON encoder to handle NaN values
        response = json.dumps({
            'success': True,
            'file_path': file_path,
            'stats': stats
        }, cls=NpEncoder)
        
        return response, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        response = json.dumps({'error': str(e)}, cls=NpEncoder)
        return response, 500, {'Content-Type': 'application/json'}

@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    """Analyze a data file and generate an enriched data dictionary"""
    data = request.json
    file_path = data.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        response = json.dumps({'error': 'Invalid file path'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    try:
        # Create data dictionary folder if it doesn't exist
        if not os.path.exists(DATA_DICT_FOLDER):
            os.makedirs(DATA_DICT_FOLDER)
        
        # Process data file
        analyzer = DataPreplanner()
        data_dict = analyzer.analyze_data(file_path)
        
        # Save data dictionary
        dataset_name = os.path.basename(file_path).split('.')[0]
        data_dict_path = os.path.join(DATA_DICT_FOLDER, f"{dataset_name}_data_dict.json")
        analyzer.save_data_dictionary(data_dict, data_dict_path, format="json")
        
        # Create SQLite database
        db_path = "csv_database.db"
        create_database_from_file(file_path, db_path)
        
        # Use custom JSON encoder to handle NaN values
        response = json.dumps({
            'success': True,
            'data_dict_path': data_dict_path,
            'db_path': db_path,
            'data_dict': data_dict
        }, cls=NpEncoder)
        
        return response, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        print(f"Error analyzing data: {str(e)}")
        response = json.dumps({'error': str(e)}, cls=NpEncoder)
        return response, 500, {'Content-Type': 'application/json'}

@app.route('/api/process_query', methods=['POST'])
def process_query():
    """Process a natural language query using the agentic approach"""
    global processor
    
    data = request.json
    query = data.get('query')
    data_dict_path = data.get('data_dict_path')
    db_path = data.get('db_path')
    
    if not query:
        response = json.dumps({'error': 'No query provided'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    if not data_dict_path or not db_path:
        response = json.dumps({'error': 'Data dictionary or database path not provided'}, cls=NpEncoder)
        return response, 400, {'Content-Type': 'application/json'}
    
    try:
        # Initialize processor if needed
        if processor is None:
            processor = AgenticQueryProcessor(
                data_dict_path=data_dict_path,
                db_path=db_path
            )
        
        # Process the query
        result = processor.process_query(query)
        
        # Convert DataFrame results to lists of dictionaries
        if isinstance(result.get('results'), pd.DataFrame):
            result['results'] = result['results'].to_dict(orient='records')
        
        # Use custom JSON encoder to handle NaN values
        response = json.dumps({
            'success': True,
            'result': result
        }, cls=NpEncoder)
        
        return response, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        response = json.dumps({'error': str(e)}, cls=NpEncoder)
        return response, 500, {'Content-Type': 'application/json'}

def create_database_from_file(file_path, db_path):
    """Create a SQLite database from a data file"""
    # Get file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Read file based on extension
    if file_ext == '.csv':
        df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
    elif file_ext == '.json':
        df = pd.read_json(file_path)
    elif file_ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
    elif file_ext == '.xml':
        import xml.etree.ElementTree as ET
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
    
    # Replace NaN values with None to avoid JSON serialization issues
    df = df.replace({np.nan: None})
    
    # Create SQLite database
    conn = sqlite3.connect(db_path)
    
    # Get table name from file name
    table_name = os.path.basename(file_path).split('.')[0]
    
    # Write DataFrame to SQLite
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    # Close connection
    conn.close()
    
    return db_path

# Serve a simple HTML interface at the root URL
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NL2SQL Tool</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1 {
                color: #2c7be5;
            }
            .container {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            .card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            input[type=file], textarea {
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            textarea {
                height: 100px;
            }
            button {
                background-color: #2c7be5;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 4px;
                cursor: pointer;
            }
            button:hover {
                background-color: #1a68d1;
            }
            #results {
                white-space: pre-wrap;
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 4px;
                display: none;
            }
        </style>
    </head>
    <body>
        <h1>NL2SQL Tool</h1>
        <p>An agentic AI application that converts natural language queries to SQL and processes them using GPT-4.1 Nano.</p>
        
        <div class="container">
            <div class="card">
                <h2>Upload Data File</h2>
                <div class="form-group">
                    <label for="file">Select a CSV, JSON, XML, or Excel file:</label>
                    <input type="file" id="file" accept=".csv,.json,.xml,.xlsx,.xls">
                </div>
                <button id="uploadBtn">Upload & Analyze</button>
                <div id="fileInfo" style="margin-top: 15px; display: none;"></div>
            </div>
            
            <div class="card">
                <h2>Query Your Data</h2>
                <div class="form-group">
                    <label for="query">Enter your query in natural language:</label>
                    <textarea id="query" placeholder="Example: What is the average value by category?"></textarea>
                </div>
                <button id="queryBtn">Process Query</button>
                <div id="results"></div>
            </div>
        </div>
        
        <script>
            let dataDictPath = null;
            let dbPath = "csv_database.db";
            
            document.getElementById('uploadBtn').addEventListener('click', async () => {
                const fileInput = document.getElementById('file');
                if (!fileInput.files.length) {
                    alert('Please select a file first');
                    return;
                }
                
                const file = fileInput.files[0];
                const formData = new FormData();
                formData.append('file', file);
                
                // Show loading message
                const fileInfo = document.getElementById('fileInfo');
                fileInfo.innerHTML = '<p>Uploading and processing file... Please wait.</p>';
                fileInfo.style.display = 'block';
                
                try {
                    // Upload file
                    console.log('Uploading file...');
                    let uploadData;
                    
                    try {
                        const uploadResponse = await fetch('/api/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        // Check if response is OK
                        if (!uploadResponse.ok) {
                            const errorText = await uploadResponse.text();
                            throw new Error(`Server error: ${uploadResponse.status} ${errorText}`);
                        }
                        
                        // Get response as text
                        const responseText = await uploadResponse.text();
                        console.log('Response text:', responseText);
                        
                        // Handle NaN values by replacing them with null
                        const cleanedText = responseText.replace(/: ?NaN/g, ': null');
                        
                        // Parse the cleaned JSON
                        uploadData = JSON.parse(cleanedText);
                        console.log('Upload data:', uploadData);
                    } catch (parseError) {
                        console.error('Error parsing upload response:', parseError);
                        throw new Error(`Failed to parse server response: ${parseError.message}`);
                    }
                    
                    if (!uploadData.success) {
                        throw new Error(uploadData.error || 'Error uploading file');
                    }
                    
                    // Display file info
                    fileInfo.innerHTML = `
                        <h3>File Information</h3>
                        <p><strong>Rows:</strong> ${uploadData.stats.rows}</p>
                        <p><strong>Columns:</strong> ${uploadData.stats.columns}</p>
                        <p><strong>Data Types:</strong> ${uploadData.stats.data_types}</p>
                        <p>Analyzing data... Please wait.</p>
                    `;
                    
                    // Analyze data
                    console.log('Analyzing data...');
                    let analyzeData;
                    
                    try {
                        const analyzeResponse = await fetch('/api/analyze', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                file_path: uploadData.file_path
                            })
                        });
                        
                        // Check if response is OK
                        if (!analyzeResponse.ok) {
                            const errorText = await analyzeResponse.text();
                            throw new Error(`Server error: ${analyzeResponse.status} ${errorText}`);
                        }
                        
                        // Get response as text
                        const responseText = await analyzeResponse.text();
                        console.log('Analyze response text:', responseText);
                        
                        // Handle NaN values by replacing them with null
                        const cleanedText = responseText.replace(/: ?NaN/g, ': null');
                        
                        // Parse the cleaned JSON
                        analyzeData = JSON.parse(cleanedText);
                        console.log('Analyze data:', analyzeData);
                    } catch (parseError) {
                        console.error('Error parsing analyze response:', parseError);
                        throw new Error(`Failed to parse server response: ${parseError.message}`);
                    }
                    
                    if (!analyzeData.success) {
                        throw new Error(analyzeData.error || 'Error analyzing data');
                    }
                    
                    dataDictPath = analyzeData.data_dict_path;
                    dbPath = analyzeData.db_path;
                    
                    // Update file info to show analysis is complete
                    fileInfo.innerHTML = `
                        <h3>File Information</h3>
                        <p><strong>Rows:</strong> ${uploadData.stats.rows}</p>
                        <p><strong>Columns:</strong> ${uploadData.stats.columns}</p>
                        <p><strong>Data Types:</strong> ${uploadData.stats.data_types}</p>
                        <p style="color: green;"><strong>✓ Analysis complete!</strong> You can now query your data.</p>
                    `;
                    
                } catch (error) {
                    console.error('Error:', error);
                    fileInfo.innerHTML = `<p style="color: red;"><strong>Error:</strong> ${error.message}</p>`;
                }
            });
            
            document.getElementById('queryBtn').addEventListener('click', async () => {
                const query = document.getElementById('query').value.trim();
                if (!query) {
                    alert('Please enter a query');
                    return;
                }
                
                if (!dataDictPath) {
                    alert('Please upload and analyze a data file first');
                    return;
                }
                
                // Show loading message
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = '<p>Processing query... This may take a moment.</p>';
                resultsDiv.style.display = 'block';
                
                try {
                    console.log('Processing query:', query);
                    let data;
                    
                    try {
                        const response = await fetch('/api/process_query', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                query,
                                data_dict_path: dataDictPath,
                                db_path: dbPath
                            })
                        });
                        
                        // Check if response is OK
                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`Server error: ${response.status} ${errorText}`);
                        }
                        
                        // Get response as text
                        const responseText = await response.text();
                        console.log('Query response text:', responseText);
                        
                        // Handle NaN values by replacing them with null
                        const cleanedText = responseText.replace(/: ?NaN/g, ': null');
                        
                        // Parse the cleaned JSON
                        data = JSON.parse(cleanedText);
                        console.log('Query data:', data);
                    } catch (parseError) {
                        console.error('Error parsing query response:', parseError);
                        throw new Error(`Failed to parse server response: ${parseError.message}`);
                    }
                    
                    if (!data.success) {
                        throw new Error(data.error || 'Error processing query');
                    }
                    
                    const result = data.result;
                    
                    // Format results as a table if it's an array of objects
                    let resultsHtml = '';
                    if (Array.isArray(result.results) && result.results.length > 0 && typeof result.results[0] === 'object') {
                        // Get all unique keys from all objects
                        const keys = Array.from(new Set(
                            result.results.flatMap(obj => Object.keys(obj))
                        ));
                        
                        resultsHtml = `
                            <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
                                <thead>
                                    <tr>
                                        ${keys.map(key => `<th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">${key}</th>`).join('')}
                                    </tr>
                                </thead>
                                <tbody>
                                    ${result.results.map(row => `
                                        <tr>
                                            ${keys.map(key => `<td style="border: 1px solid #ddd; padding: 8px;">${row[key] !== undefined ? row[key] : ''}</td>`).join('')}
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `;
                    } else {
                        resultsHtml = `<pre>${JSON.stringify(result.results, null, 2)}</pre>`;
                    }
                    
                    // Display results
                    resultsDiv.innerHTML = `
                        <h3>Results</h3>
                        <p><strong>Summary:</strong> ${result.summary}</p>
                        <h4>Query Details</h4>
                        <p><strong>Query:</strong> ${result.query}</p>
                        <p><strong>Complexity:</strong> ${result.complexity || 'Unknown'}</p>
                        <p><strong>Type:</strong> ${result.type || 'Unknown'}</p>
                        
                        <h4>Results</h4>
                        ${resultsHtml}
                    `;
                    
                } catch (error) {
                    console.error('Error:', error);
                    resultsDiv.innerHTML = `<p style="color: red;"><strong>Error:</strong> ${error.message}</p>`;
                }
            });
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True, port=5000)
