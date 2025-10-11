from flask import Flask, request, jsonify
from flask_cors import CORS
from file_processor import FileProcessor
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for Tauri frontend

processor = FileProcessor()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if the API and Ollama are working"""
    try:
        # Test Ollama connection
        import requests
        response = requests.get("http://localhost:11434/api/tags")
        ollama_status = response.status_code == 200
    except:
        ollama_status = False
    
    return jsonify({
        "status": "running",
        "ollama_connected": ollama_status
    })

@app.route('/api/process-file', methods=['POST'])
def process_file():
    """Process a single file and return tags"""
    data = request.get_json()
    
    if not data or 'file_path' not in data:
        return jsonify({"error": "file_path is required"}), 400
    
    file_path = data['file_path']
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    result = processor.process_file(file_path)
    return jsonify(result)

@app.route('/api/process-files', methods=['POST'])
def process_files():
    """Process multiple files and return tags for each"""
    data = request.get_json()
    
    if not data or 'file_paths' not in data:
        return jsonify({"error": "file_paths array is required"}), 400
    
    file_paths = data['file_paths']
    results = []
    
    for file_path in file_paths:
        if os.path.exists(file_path):
            result = processor.process_file(file_path)
            results.append(result)
        else:
            results.append({
                "filename": os.path.basename(file_path),
                "path": file_path,
                "success": False,
                "error": "File not found",
                "tags": []
            })
    
    return jsonify({"results": results})

@app.route('/api/supported-types', methods=['GET'])
def get_supported_types():
    """Get list of supported file extensions"""
    return jsonify({
        "extensions": list(processor.supported_extensions)
    })

if __name__ == '__main__':
    print("Starting Tag Sense AI Backend...")
    print("Supported file types:", processor.supported_extensions)
    app.run(debug=True, port=5000)