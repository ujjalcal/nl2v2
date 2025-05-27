import React, { useState } from 'react';
import './MessageItem.css';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';

const MessageItem = ({ message }) => {
  const [expandedSection, setExpandedSection] = useState(null);
  
  const toggleSection = (section) => {
    if (expandedSection === section) {
      setExpandedSection(null);
    } else {
      setExpandedSection(section);
    }
  };
  
  const renderDataTable = (data) => {
    if (!data || data.length === 0) return <p>No data available</p>;
    
    // Get all keys from the first item
    const keys = Object.keys(data[0]);
    
    return (
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              {keys.map((key) => (
                <th key={key}>{key}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i}>
                {keys.map((key) => (
                  <td key={key}>{row[key]?.toString() || ''}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };
  
  const renderDetails = () => {
    if (!message.details) return null;
    
    return (
      <div className="message-details">
        {message.details.stats && (
          <div className="detail-section">
            <h4 className="detail-title">File Statistics</h4>
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-value">{message.details.stats.rows}</div>
                <div className="stat-label">Rows</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{message.details.stats.columns}</div>
                <div className="stat-label">Columns</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{message.details.stats.data_types}</div>
                <div className="stat-label">Data Types</div>
              </div>
            </div>
            
            {message.details.stats.preview && (
              <>
                <h4 className="detail-title">Data Preview</h4>
                {renderDataTable(message.details.stats.preview)}
              </>
            )}
          </div>
        )}
        
        {message.details.dataDict && (
          <div className="detail-section">
            <div 
              className="collapsible-header"
              onClick={() => toggleSection('dataDict')}
            >
              <h4 className="detail-title">Data Dictionary</h4>
              {expandedSection === 'dataDict' ? <FiChevronUp /> : <FiChevronDown />}
            </div>
            
            {expandedSection === 'dataDict' && (
              <div className="collapsible-content">
                <p><strong>Dataset:</strong> {message.details.dataDict.dataset_name}</p>
                <p><strong>Description:</strong> {message.details.dataDict.description}</p>
                <p><strong>Fields:</strong> {message.details.dataDict.fields_count}</p>
                
                <h5 className="sub-title">Fields</h5>
                <div className="fields-list">
                  {Object.keys(message.details.dataDict).filter(key => 
                    !['dataset_name', 'description', 'fields_count'].includes(key)
                  ).map(field => (
                    <div key={field} className="field-item">
                      <h6>{field}</h6>
                      <p><strong>Type:</strong> {message.details.dataDict[field].type}</p>
                      <p><strong>Description:</strong> {message.details.dataDict[field].description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {message.details.query && (
          <div className="detail-section">
            <div 
              className="collapsible-header"
              onClick={() => toggleSection('query')}
            >
              <h4 className="detail-title">Query Details</h4>
              {expandedSection === 'query' ? <FiChevronUp /> : <FiChevronDown />}
            </div>
            
            {expandedSection === 'query' && (
              <div className="collapsible-content">
                <p><strong>Query:</strong> {message.details.query}</p>
                <p><strong>Complexity:</strong> {message.details.complexity || 'Unknown'}</p>
                <p><strong>Type:</strong> {message.details.type || 'Unknown'}</p>
              </div>
            )}
          </div>
        )}
        
        {message.details.reasoningSteps && (
          <div className="detail-section">
            <div 
              className="collapsible-header"
              onClick={() => toggleSection('reasoning')}
            >
              <h4 className="detail-title">Reasoning Process</h4>
              {expandedSection === 'reasoning' ? <FiChevronUp /> : <FiChevronDown />}
            </div>
            
            {expandedSection === 'reasoning' && (
              <div className="collapsible-content">
                {message.details.reasoningSteps.map((step, index) => (
                  <div key={index} className="reasoning-step">
                    <h5>{step.step_number}. {step.step_name}</h5>
                    <p>{step.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {message.details.executionPlan && (
          <div className="detail-section">
            <div 
              className="collapsible-header"
              onClick={() => toggleSection('execution')}
            >
              <h4 className="detail-title">Execution Plan</h4>
              {expandedSection === 'execution' ? <FiChevronUp /> : <FiChevronDown />}
            </div>
            
            {expandedSection === 'execution' && (
              <div className="collapsible-content">
                {message.details.executionPlan.map((step, index) => (
                  <div key={index} className="execution-step">
                    <h5>Step {step.step}</h5>
                    <p><strong>Action:</strong> {step.action}</p>
                    {step.description && <p><strong>Description:</strong> {step.description}</p>}
                    {step.query && (
                      <div className="code-block sql">
                        {step.query}
                      </div>
                    )}
                    {step.code && (
                      <div className="code-block python">
                        {step.code}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {message.details.results && (
          <div className="detail-section">
            <h4 className="detail-title">Results</h4>
            {Array.isArray(message.details.results) 
              ? renderDataTable(message.details.results)
              : <p>{JSON.stringify(message.details.results)}</p>
            }
          </div>
        )}
      </div>
    );
  };
  
  return (
    <div className={`message ${message.role}`}>
      <div className="message-content">
        <p>{message.content}</p>
        {renderDetails()}
      </div>
    </div>
  );
};

export default MessageItem;
