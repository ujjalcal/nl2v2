import React, { useState, useRef, useEffect } from 'react';
import { FiSend, FiPaperclip } from 'react-icons/fi';
import './ChatInterface.css';
import MessageItem from './MessageItem';

const ChatInterface = ({ messages, onSendMessage, onFileUpload, loading }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  
  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !loading) {
      onSendMessage(input);
      setInput('');
    }
  };
  
  const handleFileClick = () => {
    fileInputRef.current.click();
  };
  
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onFileUpload(e.target.files[0]);
      // Reset file input
      e.target.value = null;
    }
  };
  
  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.map((message, index) => (
          <MessageItem key={index} message={message} />
        ))}
        {loading && (
          <div className="message system">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <form className="input-container" onSubmit={handleSubmit}>
        <button 
          type="button" 
          className="attachment-button" 
          onClick={handleFileClick}
          disabled={loading}
        >
          <FiPaperclip />
        </button>
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileChange} 
          style={{ display: 'none' }} 
          accept=".csv,.json,.xml,.xlsx,.xls"
        />
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your query here..."
          disabled={loading}
          className="message-input"
        />
        <button 
          type="submit" 
          className="send-button" 
          disabled={!input.trim() || loading}
        >
          <FiSend />
        </button>
      </form>
    </div>
  );
};

export default ChatInterface;
