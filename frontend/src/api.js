import axios from 'axios';

// Use the exact URL from the Flask server output
const API_URL = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:5000';

// Process a message/query
export const processMessage = async (message, dataDictPath, dbPath) => {
  try {
    const response = await axios.post(`${API_URL}/api/process_query`, {
      query: message,
      data_dict_path: dataDictPath,
      db_path: dbPath
    });
    return response.data;
  } catch (error) {
    console.error('Error processing message:', error);
    throw new Error(error.response?.data?.error || 'Failed to process message');
  }
};

// Upload a file
export const uploadFile = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await axios.post(`${API_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading file:', error);
    throw new Error(error.response?.data?.error || 'Failed to upload file');
  }
};

// Analyze data
export const analyzeData = async (filePath) => {
  try {
    const response = await axios.post(`${API_URL}/api/analyze`, {
      file_path: filePath
    });
    return response.data;
  } catch (error) {
    console.error('Error analyzing data:', error);
    throw new Error(error.response?.data?.error || 'Failed to analyze data');
  }
};
