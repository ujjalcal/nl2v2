import React, { useState } from 'react';
import './Sidebar.css';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';

const Sidebar = ({ fileData, dataDict }) => {
  const [expandedSection, setExpandedSection] = useState(null);
  
  const toggleSection = (section) => {
    if (expandedSection === section) {
      setExpandedSection(null);
    } else {
      setExpandedSection(section);
    }
  };
  
  return (
    <div className="sidebar">
      <h2 className="sidebar-title">NL2SQL Tool</h2>
      
      {fileData && (
        <div className="sidebar-section">
          <div 
            className="section-header"
            onClick={() => toggleSection('fileInfo')}
          >
            <h3>File Information</h3>
            {expandedSection === 'fileInfo' ? <FiChevronUp /> : <FiChevronDown />}
          </div>
          
          {expandedSection === 'fileInfo' && (
            <div className="section-content">
              <div className="stats-container">
                <div className="stat-item">
                  <div className="stat-value">{fileData.stats.rows}</div>
                  <div className="stat-label">Rows</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{fileData.stats.columns}</div>
                  <div className="stat-label">Columns</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{fileData.stats.data_types}</div>
                  <div className="stat-label">Data Types</div>
                </div>
              </div>
              
              <h4 className="subsection-title">Data Preview</h4>
              <div className="data-preview">
                <table>
                  <thead>
                    <tr>
                      {fileData.stats.preview && fileData.stats.preview.length > 0 && 
                        Object.keys(fileData.stats.preview[0]).map((key) => (
                          <th key={key}>{key}</th>
                        ))
                      }
                    </tr>
                  </thead>
                  <tbody>
                    {fileData.stats.preview && fileData.stats.preview.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((value, j) => (
                          <td key={j}>{value !== null ? value.toString() : 'null'}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
      
      {dataDict && (
        <div className="sidebar-section">
          <div 
            className="section-header"
            onClick={() => toggleSection('dataDictionary')}
          >
            <h3>Data Dictionary</h3>
            {expandedSection === 'dataDictionary' ? <FiChevronUp /> : <FiChevronDown />}
          </div>
          
          {expandedSection === 'dataDictionary' && (
            <div className="section-content">
              <p><strong>Dataset:</strong> {dataDict.dataset_name}</p>
              <p><strong>Description:</strong> {dataDict.description}</p>
              
              <h4 className="subsection-title">Fields</h4>
              <div className="fields-list">
                {Object.keys(dataDict).filter(key => 
                  !['dataset_name', 'description', 'fields_count'].includes(key)
                ).map(field => (
                  <div key={field} className="field-item">
                    <div className="field-header">
                      <strong>{field}</strong>
                      <span className="field-type">{dataDict[field].type}</span>
                    </div>
                    <p className="field-description">{dataDict[field].description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      <div className="sidebar-section">
        <div 
          className="section-header"
          onClick={() => toggleSection('help')}
        >
          <h3>Help</h3>
          {expandedSection === 'help' ? <FiChevronUp /> : <FiChevronDown />}
        </div>
        
        {expandedSection === 'help' && (
          <div className="section-content">
            <h4 className="subsection-title">Example Queries</h4>
            <ul className="example-queries">
              <li>What is the average value by category?</li>
              <li>Show me the top 5 items by price</li>
              <li>Which products have been sold more than 100 times?</li>
              <li>Calculate the median price for each category</li>
              <li>Compare sales between regions</li>
            </ul>
            
            <h4 className="subsection-title">Tips</h4>
            <ul className="tips-list">
              <li>Upload a CSV, JSON, XML, or Excel file to get started</li>
              <li>Ask questions in natural language</li>
              <li>For complex queries, be specific about what you're looking for</li>
              <li>You can ask for explanations of the data</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
