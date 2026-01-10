from flask import Flask, request, jsonify
from flask_cors import CORS
from file_processor import FileProcessor
from ollama_client import OllamaClient
import os
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)

# --- Globals ---
# We will load the config once at startup
CONFIG = {}
def load_app_config():
    """Loads the test_config.json for API use."""
    global CONFIG
    try:
        # Assumes the script is run from the project root or Sources/Backend
        config_path = Path(__file__).parent.parent.parent / "test_config.json"
        if not config_path.exists():
             # Fallback for running from different directories
             config_path = Path("test_config.json")

        with open(config_path, 'r') as f:
            CONFIG = json.load(f)
        app.logger.info(f"Successfully loaded config from {config_path}")
    except Exception as e:
        app.logger.error(f"FATAL: Could not load test_config.json. Error: {e}")
        CONFIG = {"tags": {"text": [], "image": []}, "models": []} # Default empty config

# Initialize components
file_processor = FileProcessor()
ollama_client = OllamaClient()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if the API and Ollama are working"""
    return jsonify({
        "status": "running",
        "ollama_connected": ollama_client.is_ollama_running()
    })

@app.route('/api/process-file', methods=['POST'])
def process_file():
    """
    Process a single file. This is the core endpoint that handles dynamic
    prompt generation based on file content.
    """
    data = request.get_json()
    
    # --- Validation ---
    if not data or 'file_path' not in data:
        return jsonify({"error": "file_path is required"}), 400
    
    file_path = data['file_path']
    model_name = data.get('model')
    prompt_template = data.get('prompt_template')
    options = data.get('options')

    if not all([file_path, model_name, prompt_template, options]):
        return jsonify({"error": "Missing required fields: file_path, model, prompt_template, options"}), 400

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # --- File Processing ---
    processed_content = file_processor.read_file_content(file_path)
    if not processed_content:
        return jsonify({"error": "Failed to process file content"}), 500

    content_type = processed_content['type']
    content = processed_content['content']
    
    # --- Model and Tag Logic ---
    # Find the model's capabilities from the loaded config
    model_info = next((m for m in CONFIG.get('models', []) if m['name'] == model_name), None)
    if not model_info:
        return jsonify({"error": f"Model '{model_name}' not found in config."}), 400

    is_vision_model = 'image' in model_info.get('file_types', [])
    
    # Handle scanned PDFs: they require a vision model
    if content_type == 'image_from_pdf' and not is_vision_model:
        return jsonify({
            "error": f"Model '{model_name}' cannot process scanned PDF. A vision-capable model is required."
        }), 400

    # Determine which tag list to use
    tag_list_key = 'text' # Default to text tags
    if content_type == 'image': # Only use image tags for actual image files
        tag_list_key = 'image'
    
    # Get the actual tags and format them
    tags_to_use = CONFIG.get('tags', {}).get(tag_list_key, [])
    tag_list_str = ", ".join(tags_to_use)

    # --- Final Prompt Assembly ---
    final_prompt = prompt_template.replace('{tag_list}', tag_list_str)
    
    # For text content, we also inject the text itself
    if content_type == 'text':
        # Apply truncation before injecting
        truncated_text = file_processor._prepare_text_for_model(content, model_name)
        final_prompt = final_prompt.replace('{text}', truncated_text)
        images_payload = []
    else: # For 'image' and 'image_from_pdf'
        # The {text} placeholder is ignored for image prompts
        final_prompt = final_prompt.replace('{text}', '') # Ensure it's empty
        images_payload = [content] # The base64 content

    # --- Call Ollama ---
    try:
        tags, processing_time = ollama_client.generate_tags(
            model=model_name,
            prompt=final_prompt,
            images=images_payload,
            options=options
        )
        
        return jsonify({
            "tags": tags,
            "processing_time_ms": processing_time,
            "error": None
        })
    except Exception as e:
        app.logger.error(f"Error calling Ollama: {e}")
        return jsonify({"error": str(e)}), 500

# --- Main Execution ---
if __name__ == "__main__":
    load_app_config()
    app.logger.info("Starting Tag Sense AI Backend...")
    # Use a different port to avoid conflict with potential other services
    app.run(host='0.0.0.0', port=5000, debug=False)
