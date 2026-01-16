"""
Standalone Auto-Tagger - Monitor TestTagging folder and process files automatically
Usage: python auto_tagger.py
"""

import json
import os
import time
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    'text': {'.txt', '.docx', '.pdf'},
    'image': {'.jpg', '.jpeg', '.png'}
}

class AutoTaggerHandler(FileSystemEventHandler):
    def __init__(self, config_path, results_path, backend_url="http://127.0.0.1:5000"):
        self.config = self.load_config(config_path)
        self.results_path = results_path
        self.backend_url = backend_url
        self.processed_files = {}  # file_path -> modified_time
        self.interrupted = False  # Flag for graceful shutdown
        
        logger.info(f"Loaded {len(self.config['combinations'])} model+prompt combinations")
        logger.info(f"Monitoring folder: {self.config['test_folder']}")

    def load_config(self, config_path):
        """
        Load test configuration and generate model+prompt combinations.
        The prompt templates are NOT formatted here; the API is responsible
        for injecting the correct tag lists.
        Supports categorized prompts (e.g. text_domain, text_functional_type).
        """
        with open(config_path, 'r') as f:
            config = json.load(f)

        combinations = []
        
        def get_base_type(cat_name):
            if cat_name.startswith('text') or cat_name == 'text': return 'text'
            if cat_name.startswith('image') or cat_name == 'image': return 'image'
            return None

        for model in config['models']:
            supported_types = set(model['file_types'])
            # Iterate over all prompt categories available in config
            prompt_categories = config.get('prompts', {}).keys()
            
            for category in prompt_categories:
                base_type = get_base_type(category)
                
                # If we identify the type and the model supports it
                if base_type and base_type in supported_types:
                    type_prompts = config['prompts'][category]
                    
                    for prompt in type_prompts:
                        combo = {
                            'id': f"{model['id']}_{category}_{prompt['id']}",
                            'model': model['name'],
                            'file_types': [base_type],
                            'prompt': prompt['prompt'],
                            'options': prompt['options'],
                            'tag_category': category # Pass the specific category key
                        }
                        combinations.append(combo)
        
        config['combinations'] = combinations
        logger.info(f"Generated {len(combinations)} combinations from {len(config['models'])} models")
        
        return config
    
    def get_file_type(self, file_path):
        """Determine if file is text or image"""
        ext = Path(file_path).suffix.lower()
        if ext in SUPPORTED_EXTENSIONS['image']:
            return 'image'
        elif ext in SUPPORTED_EXTENSIONS['text']:
            return 'text'
        return None
    
    def is_supported_file(self, file_path):
        """Check if file type is supported"""
        ext = Path(file_path).suffix.lower()
        all_extensions = SUPPORTED_EXTENSIONS['text'] | SUPPORTED_EXTENSIONS['image']
        return ext in all_extensions
    
    def should_process(self, file_path):
        """Check if file should be processed based on modification time"""
        try:
            modified_time = os.path.getmtime(file_path)
            last_modified = self.processed_files.get(file_path)
            
            if last_modified is None or last_modified != modified_time:
                self.processed_files[file_path] = modified_time
                return True
            return False
        except OSError:
            return False
    
    def write_result(self, result):
        """Append result to JSON-lines file"""
        with open(self.results_path, 'a') as f:
            f.write(json.dumps(result) + '\n')
    
    def process_file_with_combo(self, file_path, combo, run_number):
        """Process a file with a specific model+prompt combination"""
        logger.info(f"  Testing: {combo['id']} (model: {combo['model']})")
        
        payload = {
            "file_path": str(file_path),
            "model": combo['model'],
            "prompt_template": combo['prompt'],
            "options": combo['options'],
            "tag_category": combo.get('tag_category')
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/process-file",
                json=payload,
                timeout=360
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "file_path": str(file_path),
                    "file_modified_time": int(os.path.getmtime(file_path)),
                    "model_name": combo['model'],
                    "prompt_id": combo['id'],
                    "run_number": run_number,
                    "tags": data.get('tags', []),
                    "processing_time_ms": data.get('processing_time_ms', elapsed_ms),
                    "error": data.get('error')
                }
                
                if result['error'] is None:
                    logger.info(f"    [OK] Success: {len(result['tags'])} tags in {result['processing_time_ms']:.2f}ms")
                    logger.info(f"    Tags: {result['tags']}")
                else:
                    logger.warning(f"    [FAIL] Failed: {result['error']}")
                
                self.write_result(result)
                
            else:
                logger.error(f"    [FAIL] Backend error: HTTP {response.status_code}")
                result = {
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "file_path": str(file_path),
                    "file_modified_time": int(os.path.getmtime(file_path)),
                    "model_name": combo['model'],
                    "prompt_id": combo['id'],
                    "run_number": run_number,
                    "tags": [],
                    "processing_time_ms": elapsed_ms,
                    "error": f"HTTP {response.status_code}"
                }
                self.write_result(result)
                
        except requests.exceptions.Timeout:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"    [FAIL] Request timeout")
            result = {
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "file_path": str(file_path),
                "file_modified_time": int(os.path.getmtime(file_path)),
                "model_name": combo['model'],
                "prompt_id": combo['id'],
                "run_number": run_number,
                "tags": [],
                "processing_time_ms": elapsed_ms,
                "error": "Request timeout"
            }
            self.write_result(result)
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"    [FAIL] Error: {e}")
            result = {
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "file_path": str(file_path),
                "file_modified_time": int(os.path.getmtime(file_path)),
                "model_name": combo['model'],
                "prompt_id": combo['id'],
                "run_number": run_number,
                "tags": [],
                "processing_time_ms": elapsed_ms,
                "error": str(e)
            }
            self.write_result(result)
    
    def process_file(self, file_path):
        """Process file through all applicable model+prompt combinations"""
        logger.info("\n" + "=" * 60)
        logger.info(f"Processing file: {file_path}")
        logger.info("=" * 60)
        
        # Determine file type
        file_type = self.get_file_type(file_path)
        if not file_type:
            logger.warning(f"Unsupported file type: {file_path}")
            return
        
        # Filter combinations by file type
        applicable_combos = [
            combo for combo in self.config['combinations']
            if file_type in combo['file_types']
        ]
        
        logger.info(f"Found {len(applicable_combos)} applicable combinations for {file_type} file")
        
        logger.info(f"Running each combination 2 times for consistency testing")
        
        total_runs = len(applicable_combos) * 2
        run_count = 0
        
        # Process with each combination sequentially, twice
        for combo in applicable_combos:
            for run_number in [1, 2]:
                if self.interrupted:
                    logger.info("\n[INTERRUPTED] Stopping processing due to interrupt signal")
                    return
                run_count += 1
                logger.info(f"\n[{run_count}/{total_runs}] Run {run_number}")
                self.process_file_with_combo(file_path, combo, run_number)
        
        logger.info(f"\n[OK] Completed processing: {file_path}\n")
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self.is_supported_file(file_path) and self.should_process(file_path):
            logger.info(f"\n-> New file detected: {file_path}")
            # Small delay to ensure file is fully written
            time.sleep(1.5)
            self.process_file(file_path)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self.is_supported_file(file_path) and self.should_process(file_path):
            logger.info(f"\n-> Modified file detected: {file_path}")
            # Small delay to ensure file is fully written
            time.sleep(2.0)
            self.process_file(file_path)


def check_and_start_ollama():
    """Check if Ollama is running and start it if not"""
    try:
        # Check if running using tasklist on Windows
        if os.name == 'nt':
            # Use tasklist to check for ollama.exe or ollama app.exe
            output = subprocess.check_output('tasklist', shell=True).decode('utf-8', errors='ignore')
            if 'ollama.exe' in output.lower() or 'ollama app.exe' in output.lower():
                logger.info("✓ Ollama process found running")
                return True
        
        logger.warning("Ollama process not found. Attempting to start...")
        
        # 1. Try to start 'ollama serve' (CLI) first as it's easier to hide
        try:
            logger.info("Attempting to start 'ollama serve'...")
            if os.name == 'nt':
                # Configure startup info to hide window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                # CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(['ollama', 'serve'], 
                               creationflags=0x08000000,
                               startupinfo=startupinfo)
            else:
                subprocess.Popen(['ollama', 'serve'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                
            logger.info("Waiting for Ollama to start...")
            time.sleep(5)
            return True
        except FileNotFoundError:
            logger.warning("'ollama' command not found in PATH.")
        except Exception as e:
            logger.warning(f"Failed to start 'ollama serve': {e}")

        # 2. Fallback: Try to start the Windows GUI App (System Tray version)
        if os.name == 'nt':
            # Standard installation path for Ollama on Windows
            app_path = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama app.exe")
            
            if os.path.exists(app_path):
                logger.info(f"Launching Ollama App...")
                
                # Configure startup info to hide window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE  # 0 = Hide
                
                # Launch with hidden window
                subprocess.Popen([app_path], close_fds=True, startupinfo=startupinfo)
                
                logger.info("Waiting for Ollama to start...")
                time.sleep(5)
                return True

        logger.error("Could not start Ollama. Please start it manually.")
        return False
        
    except Exception as e:
        logger.error(f"Error checking/starting Ollama: {e}")
        # Don't return False here, as we might still be able to connect if the check failed but it's running
        return False

def main():
    """Main function"""
    # Get project root (assuming we're in Sources/Backend/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    config_path = project_root / "test_config.json"
    results_path = project_root / "test_results.jsonl"
    test_folder = project_root / "TestTagging"
    
    # Verify paths exist
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return
    
    if not test_folder.exists():
        logger.error(f"Test folder not found: {test_folder}")
        return
    
    # Check and start Ollama if needed
    check_and_start_ollama()
    
    # Check backend connection
    try:
        response = requests.get("http://127.0.0.1:5000/api/health", timeout=5)
        if response.status_code != 200:
            logger.error("Backend is not responding. Please start the Flask API first.")
            return
        logger.info("✓ Backend connection verified")
    except Exception as e:
        logger.error(f"Cannot connect to backend: {e}")
        logger.error("Please start the Flask API with: python tagging_api.py")
        return
    
    # Set up file watcher
    event_handler = AutoTaggerHandler(config_path, results_path)
    observer = Observer()
    observer.schedule(event_handler, str(test_folder), recursive=True)
    observer.start()
    
    logger.info("=" * 60)
    logger.info("Auto-Tagger Started")
    logger.info("=" * 60)
    logger.info(f"Watching: {test_folder}")
    logger.info(f"Results:  {results_path}")
    logger.info("Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPT] Ctrl+C detected - stopping immediately...")
        event_handler.interrupted = True
        observer.stop()
        observer.join()
        logger.info("Auto-tagger stopped")
        return
    
    observer.join()
    logger.info("Auto-tagger stopped")


if __name__ == "__main__":
    main()
