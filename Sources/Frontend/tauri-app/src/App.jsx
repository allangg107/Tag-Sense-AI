import React, { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/tauri";
import { open } from "@tauri-apps/api/dialog";
import "./styles.css";

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [ollamaStatus, setOllamaStatus] = useState(true);
  const [statusError, setStatusError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [customPrompt, setCustomPrompt] = useState("");
  const [currentModel, setCurrentModel] = useState("TinyLlama");
  const [processingResults, setProcessingResults] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState("");
  const [editingTag, setEditingTag] = useState(null); // { resultId, tagIndex, value }

  useEffect(() => {
    checkBackendStatus();
  }, []);

  const checkBackendStatus = async () => {
    try {
      setBackendStatus("checking");
      setStatusError(null);
      
      const status = await invoke("check_backend_status");
      
      if (status.backend_connected && status.ollama_connected) {
        setBackendStatus("connected");
        setOllamaStatus(true);
      } else if (status.backend_connected && !status.ollama_connected) {
        setBackendStatus("ollama-disconnected");
        setOllamaStatus(false);
        setStatusError(status.error_message || "Ollama is not running");
      } else {
        setBackendStatus("disconnected");
        setOllamaStatus(false);
        setStatusError(status.error_message || "Backend connection failed");
      }
    } catch (error) {
      console.error("Backend check failed:", error);
      setBackendStatus("disconnected");
      setOllamaStatus(false);
      setStatusError("Failed to connect to backend");
    }
  };

  const selectFile = async () => {
    try {
      const filePath = await open({
        filters: [
          { name: "All Supported", extensions: ["txt", "md", "py", "js", "html", "css", "json", "xml", "docx", "pdf", "jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "tif"] },
          { name: "Text Files", extensions: ["txt", "md", "py", "js", "html", "css", "json", "xml"] },
          { name: "Documents", extensions: ["docx", "pdf"] },
          { name: "Images", extensions: ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "tif"] }
        ]
      });
      
      if (filePath) {
        setSelectedFile(filePath);
        setSelectedFolder(null);
        console.log("Selected file:", filePath);
      }
    } catch (error) {
      console.error("File selection failed:", error);
    }
  };

  const selectFolder = async () => {
    try {
      const folderPath = await open({
        directory: true
      });
      
      if (folderPath) {
        setSelectedFolder(folderPath);
        setSelectedFile(null);
        console.log("Selected folder:", folderPath);
      }
    } catch (error) {
      console.error("Folder selection failed:", error);
    }
  };

  const processFile = async () => {
    if (!selectedFile) return;
    
    setIsProcessing(true);
    setProcessingStatus("Processing file...");
    setCurrentModel("Detecting...");
    
    try {
      const result = await invoke("process_file_for_tags", {
        filePath: selectedFile,
        customPrompt: customPrompt.trim() || undefined
      });
      
      setCurrentModel(result.model || "Unknown");
      const newResult = {
        id: Date.now(),
        type: "file",
        path: selectedFile,
        model: result.model,
        tags: result.tags,
        success: result.success,
        error: result.error,
        timestamp: new Date().toLocaleTimeString()
      };
      
      setProcessingResults(prev => [newResult, ...prev]);
      setProcessingStatus(result.success ? "File processed successfully!" : "Processing failed");
      
      // If processing failed, check if it might be an Ollama issue
      if (!result.success && result.error && result.error.includes("Ollama")) {
        setTimeout(() => checkBackendStatus(), 1000); // Recheck status after a second
      }
    } catch (error) {
      console.error("Processing error:", error);
      const errorMessage = error.toString();
      
      // Check if error suggests Ollama connectivity issues
      if (errorMessage.includes("connection") || errorMessage.includes("timeout") || errorMessage.includes("Ollama")) {
        setProcessingStatus("Connection error - checking Ollama status...");
        setTimeout(() => checkBackendStatus(), 1000);
      } else {
        setProcessingStatus("Error processing file");
      }
      
      const errorResult = {
        id: Date.now(),
        type: "file",
        path: selectedFile,
        model: "Error",
        tags: [],
        success: false,
        error: errorMessage,
        timestamp: new Date().toLocaleTimeString()
      };
      setProcessingResults(prev => [errorResult, ...prev]);
    } finally {
      setIsProcessing(false);
    }
  };

  const processFolder = async () => {
    if (!selectedFolder) return;
    
    setIsProcessing(true);
    setProcessingStatus("Starting folder processing...");
    setCurrentModel("Multiple Models");
    
    try {
      // First, get the list of files in the folder
      const fileListResult = await invoke("get_folder_files", {
        folderPath: selectedFolder
      });
      
      if (!fileListResult.success) {
        throw new Error(fileListResult.error || "Failed to get folder files");
      }
      
      const files = fileListResult.files || [];
      setProcessingStatus(`Processing ${files.length} files...`);
      
      let processedCount = 0;
      let successCount = 0;
      let errorCount = 0;
      
      // Process each file individually
      for (const filePath of files) {
        try {
          setProcessingStatus(`Processing file ${processedCount + 1}/${files.length}: ${filePath.split('\\').pop()}`);
          
          const result = await invoke("process_file_for_tags", {
            filePath: filePath,
            customPrompt: customPrompt.trim() || undefined
          });
          
          // Add result immediately to the list
          const newResult = {
            id: Date.now() + processedCount, // Ensure unique IDs
            type: "file",
            path: filePath,
            model: result.model,
            tags: result.tags,
            success: result.success,
            error: result.error,
            timestamp: new Date().toLocaleTimeString(),
            fromFolder: selectedFolder // Mark that this came from folder processing
          };
          
          setProcessingResults(prev => [newResult, ...prev]);
          
          if (result.success) {
            successCount++;
          } else {
            errorCount++;
          }
          
        } catch (error) {
          console.error(`Error processing file ${filePath}:`, error);
          
          // Add error result immediately
          const errorResult = {
            id: Date.now() + processedCount,
            type: "file",
            path: filePath,
            model: "Error",
            tags: [],
            success: false,
            error: error.toString(),
            timestamp: new Date().toLocaleTimeString(),
            fromFolder: selectedFolder
          };
          
          setProcessingResults(prev => [errorResult, ...prev]);
          errorCount++;
        }
        
        processedCount++;
      }
      
      setProcessingStatus(`Folder processing complete: ${successCount} successful, ${errorCount} failed out of ${files.length} files`);
      
    } catch (error) {
      console.error("Folder processing error:", error);
      setProcessingStatus("Error starting folder processing");
    } finally {
      setIsProcessing(false);
    }
  };

  const clearResults = () => {
    setProcessingResults([]);
    setProcessingStatus("");
  };

  const removeTag = (resultId, tagIndex) => {
    setProcessingResults(prev => 
      prev.map(result => {
        if (result.id === resultId) {
          const newTags = [...result.tags];
          newTags.splice(tagIndex, 1);
          return { ...result, tags: newTags };
        }
        return result;
      })
    );
  };

  const startEditingTag = (resultId, tagIndex, currentValue) => {
    setEditingTag({ resultId, tagIndex, value: currentValue });
  };

  const cancelEditingTag = () => {
    setEditingTag(null);
  };

  const saveEditedTag = (resultId, tagIndex, newValue) => {
    if (newValue.trim() === '') {
      // If empty, remove the tag
      removeTag(resultId, tagIndex);
    } else {
      // Update the tag with new value
      setProcessingResults(prev => 
        prev.map(result => {
          if (result.id === resultId) {
            const newTags = [...result.tags];
            newTags[tagIndex] = newValue.trim();
            return { ...result, tags: newTags };
          }
          return result;
        })
      );
    }
    setEditingTag(null);
  };

  const handleTagKeyPress = (e, resultId, tagIndex) => {
    if (e.key === 'Enter') {
      saveEditedTag(resultId, tagIndex, e.target.value);
    } else if (e.key === 'Escape') {
      cancelEditingTag();
    }
  };

  const renderFileResult = (result) => (
    <div key={result.id} className="result-item">
      <div className="result-header">
        <span className="result-type">
          📄 File
          {result.fromFolder && <span className="folder-badge"> (from folder)</span>}
        </span>
        <span className="result-timestamp">{result.timestamp}</span>
      </div>
      <div className="result-path">{result.path}</div>
      {result.fromFolder && (
        <div className="folder-source">Source folder: {result.fromFolder}</div>
      )}
      <div className="result-model">Model: {result.model}</div>
      {result.success ? (
        <div className="tags-container">
          {result.tags && result.tags.length > 0 ? (
            result.tags.map((tag, index) => {
              const isEditing = editingTag && 
                editingTag.resultId === result.id && 
                editingTag.tagIndex === index;
              
              return (
                <span key={index} className={`tag ${isEditing ? 'editing' : ''}`}>
                  {isEditing ? (
                    <input
                      type="text"
                      className="tag-input"
                      value={editingTag.value}
                      onChange={(e) => setEditingTag({ ...editingTag, value: e.target.value })}
                      onKeyDown={(e) => handleTagKeyPress(e, result.id, index)}
                      onBlur={() => saveEditedTag(result.id, index, editingTag.value)}
                      autoFocus
                    />
                  ) : (
                    <span 
                      className="tag-text"
                      onClick={() => startEditingTag(result.id, index, tag)}
                      title="Click to edit"
                    >
                      {tag}
                    </span>
                  )}
                  <button 
                    className="tag-remove" 
                    onClick={() => removeTag(result.id, index)}
                    title="Remove tag"
                  >
                    ×
                  </button>
                </span>
              );
            })
          ) : (
            <span className="no-tags">No tags generated</span>
          )}
        </div>
      ) : (
        <div className="error-message">❌ {result.error}</div>
      )}
    </div>
  );

  return (
    <div className="app">
      <div className="left-panel">
        <div className="app-header">
          <h1>🏷️ Tag Sense AI</h1>
          <div className={`status ${backendStatus}`}>
            {backendStatus === "checking" && "🔄 Checking connection..."}
            {backendStatus === "connected" && "✅ Ready to process files"}
            {backendStatus === "ollama-disconnected" && "⚠️ Ollama not running"}
            {backendStatus === "disconnected" && "❌ Backend disconnected"}
          </div>
          {statusError && (
            <div className="status-error">
              {statusError}
              {backendStatus === "ollama-disconnected" && (
                <div className="status-help">
                  Start Ollama and <button onClick={checkBackendStatus} className="retry-btn">retry connection</button>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="controls-section">
          <h3>File Selection</h3>
          <div className="button-group">
            <button 
              className="select-button file-button" 
              onClick={selectFile}
              disabled={isProcessing}
            >
              📄 Select File
            </button>
            <button 
              className="select-button folder-button" 
              onClick={selectFolder}
              disabled={isProcessing}
            >
              📁 Select Folder
            </button>
          </div>
          
          {selectedFile && (
            <div className="selected-item">
              <strong>Selected File:</strong>
              <div className="selected-path">{selectedFile}</div>
            </div>
          )}
          
          {selectedFolder && (
            <div className="selected-item">
              <strong>Selected Folder:</strong>
              <div className="selected-path">{selectedFolder}</div>
            </div>
          )}
        </div>

        <div className="prompt-section">
          <h3>Custom Prompt (Optional)</h3>
          <textarea
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="Enter custom tagging instructions..."
            className="prompt-input"
            disabled={isProcessing}
            rows={4}
          />
        </div>

        <div className="action-section">
          <div className="button-group">
            <button 
              className="process-button file-process" 
              onClick={processFile}
              disabled={isProcessing || !selectedFile || !ollamaStatus}
              title={!ollamaStatus ? "Ollama is not running" : ""}
            >
              {isProcessing && selectedFile ? "⏳ Processing File..." : "🔄 Process File"}
            </button>
            <button 
              className="process-button folder-process" 
              onClick={processFolder}
              disabled={isProcessing || !selectedFolder || !ollamaStatus}
              title={!ollamaStatus ? "Ollama is not running" : ""}
            >
              {isProcessing && selectedFolder ? "⏳ Processing Folder..." : "🔄 Process Folder"}
            </button>
          </div>
          
          <button 
            className="clear-button" 
            onClick={clearResults}
            disabled={isProcessing || processingResults.length === 0}
          >
            🗑️ Clear Results
          </button>
        </div>

        <div className="status-section">
          <div className="current-model">
            <strong>Current Model:</strong> {currentModel}
          </div>
          {processingStatus && (
            <div className="processing-status">{processingStatus}</div>
          )}
        </div>
      </div>

      <div className="right-panel">
        <h2>Processing Results</h2>
        <div className="results-container">
          {processingResults.length === 0 ? (
            <div className="no-results">
              <p>No results yet. Select a file or folder and click process to get started!</p>
            </div>
          ) : (
            processingResults.map(result => renderFileResult(result))
          )}
        </div>
      </div>
    </div>
  );
}

export default App;