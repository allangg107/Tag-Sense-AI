import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/tauri";
import { open } from "@tauri-apps/api/dialog";

function App() {
  const [selectedFile, setSelectedFile] = useState("");
  const [tagContext, setTagContext] = useState("");
  const [generatedTags, setGeneratedTags] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [error, setError] = useState("");

  // Check backend connection on app start
  useEffect(() => {
    checkBackendConnection();
  }, []);

  const checkBackendConnection = async () => {
    try {
      const result = await invoke("check_backend_status");
      setIsBackendConnected(result);
    } catch (error) {
      console.error("Failed to check backend status:", error);
      setIsBackendConnected(false);
    }
  };

  const selectFile = async () => {
    try {
      const selected = await open({
        multiple: false,
        filters: [
          {
            name: "Text Files",
            extensions: ["txt", "md", "py", "js", "html", "css", "json", "xml", "docx", "pdf"]
          }
        ]
      });
      
      if (selected) {
        setSelectedFile(selected);
        setError("");
      }
    } catch (error) {
      console.error("Error selecting file:", error);
      setError("Failed to select file");
    }
  };

  const generateTags = async () => {
    if (!selectedFile) {
      setError("Please select a file first");
      return;
    }
    
    setIsLoading(true);
    setGeneratedTags([]);
    setError("");

    try {
      const result = await invoke("process_file_for_tags", {
        filePath: selectedFile,
        context: tagContext.trim() || null
      });
      
      if (result.success) {
        setGeneratedTags(result.tags || []);
        if (result.tags.length === 0) {
          setError("No tags were generated for this file");
        }
      } else {
        setError(result.error || "Failed to process file");
      }
    } catch (error) {
      console.error("Error:", error);
      setError(`Error: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && e.ctrlKey) {
      generateTags();
    }
  };

  return (
    <div className="app">
      <div className="header">
        <h1>🏷️ Tag Sense AI</h1>
        <p>Generate intelligent tags for your files using TinyLlama</p>
      </div>

      <div className="status-indicator">
        <div className={`status-dot ${isBackendConnected ? 'status-connected' : 'status-disconnected'}`}></div>
        <span>
          {isBackendConnected ? "Backend connected" : "Backend not available"}
        </span>
        <button 
          onClick={checkBackendConnection}
          style={{ 
            marginLeft: '10px', 
            padding: '2px 8px', 
            fontSize: '0.8rem',
            border: '1px solid #ccc',
            borderRadius: '4px',
            cursor: 'pointer',
            backgroundColor: '#f8f9fa'
          }}
        >
          Refresh
        </button>
      </div>

      <div className="tagging-container">
        <div className="file-selection">
          <h3>1. Select File to Tag</h3>
          <div className="file-picker">
            <button
              className="select-file-button"
              onClick={selectFile}
              disabled={isLoading}
            >
              📁 Choose File
            </button>
            {selectedFile && (
              <div className="selected-file">
                <span className="file-icon">📄</span>
                <span className="file-name">{selectedFile.split('\\').pop()}</span>
              </div>
            )}
          </div>
        </div>

        <div className="context-section">
          <h3>2. Add Context (Optional)</h3>
          <textarea
            className="context-input"
            value={tagContext}
            onChange={(e) => setTagContext(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Describe what kind of tags you're looking for, or provide context about the file content... (optional)"
            disabled={isLoading || !isBackendConnected}
            rows={3}
          />
        </div>
        
        <div className="action-section">
          <button
            className="generate-button"
            onClick={generateTags}
            disabled={isLoading || !selectedFile || !isBackendConnected}
          >
            {isLoading ? "🔄 Generating Tags..." : "🏷️ Generate Tags"}
          </button>
        </div>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        <div className="results-section">
          <h3>Generated Tags:</h3>
          <div className="tags-container">
            {isLoading ? (
              <div className="loading-tags">
                🤔 TinyLlama is analyzing your file...
              </div>
            ) : generatedTags.length > 0 ? (
              <div className="tags-list">
                {generatedTags.map((tag, index) => (
                  <span key={index} className="tag-item">
                    {tag}
                  </span>
                ))}
              </div>
            ) : (
              <div className="no-tags">
                Select a file and click "Generate Tags" to get started!
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{ marginTop: '2rem', fontSize: '0.9rem', color: '#718096', textAlign: 'center' }}>
        <p>💡 Tip: Use Ctrl+Enter in the context box to quickly generate tags</p>
      </div>
    </div>
  );
}

export default App;