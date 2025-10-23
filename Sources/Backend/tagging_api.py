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

@app.route('/api/get-folder-files', methods=['POST'])
def get_folder_files():
    """Get list of all supported files in a folder"""
    data = request.get_json()
    
    if not data or 'folder_path' not in data:
        return jsonify({"error": "folder_path is required"}), 400
    
    folder_path = data['folder_path']
    
    if not os.path.exists(folder_path):
        return jsonify({"error": "Folder not found"}), 404
    
    if not os.path.isdir(folder_path):
        return jsonify({"error": "Path is not a directory"}), 400
    
    # Log the request for debugging
    print(f"Getting file list for folder: {folder_path}")
    
    try:
        files = processor.get_supported_files_in_folder(folder_path)
        print(f"Found {len(files)} supported files in folder")
        return jsonify({
            "success": True,
            "files": files,
            "count": len(files)
        })
    except Exception as e:
        print(f"Error getting folder files: {e}")
        return jsonify({
            "success": False,
            "error": f"Error getting folder files: {str(e)}",
            "files": [],
            "count": 0
        }), 500

@app.route('/api/process-folder', methods=['POST'])
def process_folder():
    """Process all supported files in a folder and return tags for each"""
    data = request.get_json()
    
    if not data or 'folder_path' not in data:
        return jsonify({"error": "folder_path is required"}), 400
    
    folder_path = data['folder_path']
    
    if not os.path.exists(folder_path):
        return jsonify({"error": "Folder not found"}), 404
    
    if not os.path.isdir(folder_path):
        return jsonify({"error": "Path is not a directory"}), 400
    
    # Log the request for debugging
    print(f"Processing folder: {folder_path}")
    
    try:
        result = processor.process_folder(folder_path)
        print(f"Folder processing result: {result.get('success', False)} - {result.get('summary', {})}")
        return jsonify(result)
    except Exception as e:
        print(f"Error processing folder: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal processing error: {str(e)}",
            "results": [],
            "summary": {"total": 0, "processed": 0, "errors": 0}
        }), 500

@app.route('/api/process-file', methods=['POST'])
def process_file():
    """Process a single file and return tags"""
    data = request.get_json()
    
    if not data or 'file_path' not in data:
        return jsonify({"error": "file_path is required"}), 400
    
    file_path = data['file_path']
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    # Log the request for debugging
    print(f"Processing file: {file_path}")
    
    try:
        result = processor.process_file(file_path)
        print(f"Processing result: {result.get('success', False)} - {len(result.get('tags', []))} tags")
        return jsonify(result)
    except Exception as e:
        print(f"Error processing file: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal processing error: {str(e)}",
            "tags": []
        }), 500

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
        "text_extensions": list(processor.text_extensions),
        "image_extensions": list(processor.image_extensions),
        "all_extensions": list(processor.supported_extensions)
    })

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """Check which models are available in Ollama"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json()
            model_names = [model.get('name', '') for model in models.get('models', [])]
            
            return jsonify({
                "available_models": model_names,
                "tinyllama_available": any('tinyllama' in name.lower() for name in model_names),
                "vision_available": any('llama3.2-vision' in name.lower() or 'vision' in name.lower() for name in model_names)
            })
        else:
            return jsonify({"error": "Could not connect to Ollama"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Error checking models: {str(e)}"}), 500

def warm_up_models():
    """Warm up models by sending small test requests"""
    print("Warming up AI models...")
    
    try:
        # Warm up TinyLlama
        import requests
        tiny_payload = {
            "model": "tinyllama",
            "prompt": "Hello",
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 1}
        }
        response = requests.post("http://localhost:11434/api/generate", json=tiny_payload, timeout=10)
        if response.status_code == 200:
            print("✓ TinyLlama warmed up")
    except:
        print("! TinyLlama warmup failed")
    
    try:
        # Warm up Vision model
        vision_payload = {
            "model": "llama3.2-vision:11b",
            "prompt": "Test",
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 1}
        }
        response = requests.post("http://localhost:11434/api/generate", json=vision_payload, timeout=30)
        if response.status_code == 200:
            print("✓ Llama 3.2 Vision 11b warmed up")
    except:
        print("! Vision model warmup failed (this is normal if it's not installed)")

if __name__ == '__main__':
    print("Starting Tag Sense AI Backend...")
    print("Supported file types:", processor.supported_extensions)
    
    # Only warm up models in the main reloader process (not in the initial process)
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # Warm up models in a separate thread to not block startup
        import threading
        warmup_thread = threading.Thread(target=warm_up_models)
        warmup_thread.daemon = True
        warmup_thread.start()
    else:
        print("Skipping model warmup in initial process (will warmup after reloader starts)...")
    
    app.run(debug=True, port=5000, threaded=True)