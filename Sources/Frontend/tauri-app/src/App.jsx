import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/tauri";

function App() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  // Check Ollama connection on app start
  useEffect(() => {
    checkConnection();
  }, []);

  const checkConnection = async () => {
    try {
      const result = await invoke("check_ollama_status");
      setIsConnected(result);
    } catch (error) {
      console.error("Failed to check Ollama status:", error);
      setIsConnected(false);
    }
  };

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    
    setIsLoading(true);
    setResponse("");

    try {
      const result = await invoke("send_prompt_to_tinyllama", {
        prompt: prompt.trim()
      });
      setResponse(result);
    } catch (error) {
      console.error("Error:", error);
      setResponse(`Error: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && e.ctrlKey) {
      handleSubmit();
    }
  };

  return (
    <div className="app">
      <div className="header">
        <h1>🦙 Tag Sense AI</h1>
        <p>Chat with TinyLlama through Ollama</p>
      </div>

      <div className="status-indicator">
        <div className={`status-dot ${isConnected ? 'status-connected' : 'status-disconnected'}`}></div>
        <span>
          {isConnected ? "Connected to Ollama" : "Ollama not available"}
        </span>
        <button 
          onClick={checkConnection}
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

      <div className="chat-container">
        <div className="input-section">
          <textarea
            className="text-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Type your message to TinyLlama here... (Ctrl+Enter to send)"
            disabled={isLoading || !isConnected}
          />
          
          <button
            className="send-button"
            onClick={handleSubmit}
            disabled={isLoading || !prompt.trim() || !isConnected}
          >
            {isLoading ? "Sending..." : "Send to TinyLlama"}
          </button>
        </div>

        <div className="response-section">
          <h3>Response:</h3>
          <div className={`response-box ${isLoading ? 'loading' : ''} ${response.startsWith('Error:') ? 'error' : ''}`}>
            {isLoading ? "TinyLlama is thinking..." : response || "No response yet. Send a message to get started!"}
          </div>
        </div>
      </div>

      <div style={{ marginTop: '2rem', fontSize: '0.9rem', color: '#718096', textAlign: 'center' }}>
        <p>💡 Tip: Use Ctrl+Enter to send your message quickly</p>
      </div>
    </div>
  );
}

export default App;