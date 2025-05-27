import React, { useState, useEffect } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';
import { processMessage, uploadFile, analyzeData } from './api';

function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fileData, setFileData] = useState(null);
  const [dataDictPath, setDataDictPath] = useState(null);
  const [dbPath, setDbPath] = useState('csv_database.db');
  const [dataDict, setDataDict] = useState(null);
  const [showSidebar, setShowSidebar] = useState(true);

  // Add system welcome message on first load
  useEffect(() => {
    setMessages([
      {
        role: 'system',
        content: 'Welcome to the NL2SQL Tool! Upload a data file to get started.'
      }
    ]);
  }, []);

  const handleSendMessage = async (message) => {
    if (!message.trim()) return;

    // Add user message to chat
    const newMessages = [
      ...messages,
      { role: 'user', content: message }
    ];
    setMessages(newMessages);
    setLoading(true);

    try {
      if (!dataDictPath || !dbPath) {
        // If no data is loaded, respond with a prompt to upload data
        setMessages([
          ...newMessages,
          { 
            role: 'system', 
            content: 'Please upload a data file first to enable query processing.' 
          }
        ]);
        setLoading(false);
        return;
      }

      // Process the query
      const response = await processMessage(message, dataDictPath, dbPath);
      
      if (response.success) {
        const result = response.result;
        
        // Format the response
        let systemResponse = {
          role: 'system',
          content: result.summary || 'Query processed successfully.',
          details: {
            query: result.query,
            complexity: result.complexity,
            type: result.type,
            reasoningSteps: result.reasoning_steps,
            executionPlan: result.execution_plan,
            results: result.results
          }
        };
        
        setMessages([...newMessages, systemResponse]);
      } else {
        setMessages([
          ...newMessages,
          { role: 'system', content: `Error: ${response.error}` }
        ]);
      }
    } catch (error) {
      setMessages([
        ...newMessages,
        { role: 'system', content: `Error: ${error.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file) => {
    setLoading(true);
    try {
      // Upload file
      const uploadResponse = await uploadFile(file);
      
      if (uploadResponse.success) {
        setFileData(uploadResponse);
        
        // Add file upload message to chat
        setMessages([
          ...messages,
          { role: 'user', content: `Uploaded file: ${file.name}` },
          { 
            role: 'system', 
            content: 'File uploaded successfully. Analyzing data...',
            details: {
              stats: uploadResponse.stats
            }
          }
        ]);
        
        // Analyze data
        const analyzeResponse = await analyzeData(uploadResponse.file_path);
        
        if (analyzeResponse.success) {
          setDataDictPath(analyzeResponse.data_dict_path);
          setDbPath(analyzeResponse.db_path);
          setDataDict(analyzeResponse.data_dict);
          
          setMessages(prevMessages => [
            ...prevMessages,
            { 
              role: 'system', 
              content: 'Data analysis complete. You can now ask questions about your data.',
              details: {
                dataDict: analyzeResponse.data_dict
              }
            }
          ]);
        } else {
          setMessages(prevMessages => [
            ...prevMessages,
            { role: 'system', content: `Error analyzing data: ${analyzeResponse.error}` }
          ]);
        }
      } else {
        setMessages([
          ...messages,
          { role: 'user', content: `Attempted to upload file: ${file.name}` },
          { role: 'system', content: `Error uploading file: ${uploadResponse.error}` }
        ]);
      }
    } catch (error) {
      setMessages([
        ...messages,
        { role: 'user', content: `Attempted to upload file: ${file.name}` },
        { role: 'system', content: `Error: ${error.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSidebar = () => {
    setShowSidebar(!showSidebar);
  };

  return (
    <div className="app">
      {showSidebar && (
        <Sidebar 
          fileData={fileData} 
          dataDict={dataDict}
        />
      )}
      <main className={`main-content ${showSidebar ? '' : 'full-width'}`}>
        <button className="toggle-sidebar" onClick={toggleSidebar}>
          {showSidebar ? '←' : '→'}
        </button>
        <ChatInterface 
          messages={messages} 
          onSendMessage={handleSendMessage} 
          onFileUpload={handleFileUpload}
          loading={loading}
        />
      </main>
    </div>
  );
}

export default App;
