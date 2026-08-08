# Auto-Tagging Test System

## Overview

This system automatically monitors the `TestTagging` folder and processes any new or modified files through multiple model+prompt combinations for comparative testing.

**Two Options:**
1. **Standalone Python Script** (Recommended): Run `python auto_tagger.py` - no frontend needed
2. **Tauri Frontend**: File watching integrated into the app

## Quick Start (Python Script)

```powershell
# Single command - starts everything
.\start_auto_tagger.ps1
```

Now drop files into the `TestTagging` folder and they'll be automatically processed!

**What it does:**
- Checks if backend is running (starts it if needed)
- Starts the file watcher
- Monitors TestTagging folder
- Processes each file through all model+prompt combinations
- Saves results to test_results.jsonl

## How It Works

1. **File Watching**: The system monitors the `TestTagging` folder for new or modified files
2. **Sequential Testing**: Each file is processed through all applicable model+prompt combinations defined in `test_config.json`
3. **Results Logging**: All test results are saved to `test_results.jsonl` with detailed statistics

## Configuration

### test_config.json

Located at the project root, this file defines the testing matrix:

```json
{
  "test_folder": "TestTagging",
  "model_prompt_combinations": [
    {
      "id": "unique_identifier",
      "model": "model_name",
      "file_types": ["text" or "image"],
      "prompt": "prompt text with {text} placeholder for text files",
      "options": {
        "temperature": 0.3,
        "num_predict": 50
      }
    }
  ]
}
```

Currently configured combinations:
- **Text Files**: 3 variations using TinyLlama model
- **Image Files**: 3 variations using Llama 3.2 Vision model

## Usage

### Option 1: Standalone Python Script (Recommended)

1. **Start the Auto-Tagger** (from project root):
   ```powershell
   .\start_auto_tagger.ps1
   ```

   This will:
   - Activate the virtual environment
   - Check if backend is running (start it if needed)
   - Launch the file watcher

2. **Add Test Files**:
   - Place any supported file in the `TestTagging` folder
   - The auto-tagger will automatically detect and process it

**Advantages:**
- No frontend needed
- Lighter weight
- Runs in background
- Easy to debug

### Option 2: Tauri Frontend

1. **Start the Application**:
   ```powershell
   .\start.ps1
   ```

2. **Add Test Files**:
   - Place any supported file in the `TestTagging` folder
   - Supported formats: `.txt`, `.md`, `.py`, `.js`, `.html`, `.css`, `.json`, `.xml`, `.docx`, `.pdf`, `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.tiff`, `.tif`

3. **Automatic Processing**:
   - The system detects the new file
   - Runs all applicable model+prompt combinations sequentially
   - Logs progress to console
   - Saves results to `test_results.jsonl`

## Results

### Console Output

For each file, you'll see:
```
========================================
Processing file: "TestTagging/sample.txt"
========================================
Found 3 applicable model+prompt combinations for text file

[1/3] Testing: tinyllama_default (model: tinyllama)
  ✓ Success: 5 tags in 1234.56ms
  Tags: ["ai", "machine-learning", "technology", ...]

[2/3] Testing: tinyllama_detailed (model: tinyllama)
  ...
```

### test_results.jsonl

Each line is a JSON object containing:
```json
{
  "timestamp": "2025-12-20T10:30:45Z",
  "file_path": "C:\\...\\TestTagging\\sample.txt",
  "file_modified_time": 1734692445,
  "model_name": "tinyllama",
  "prompt_id": "tinyllama_default",
  "tags": ["ai", "machine-learning", "technology"],
  "processing_time_ms": 1234.56,
  "error": null
}
```

**Note:** Success is determined by `error` being `null`. If `error` has a value, the processing failed.

## Analysis

Import `test_results.jsonl` into Excel, Python (pandas), or any tool that supports JSON-lines format to analyze:
- Average processing time per model
- Tag quality comparison across prompts
- Success rates
- Error patterns

Example Python analysis:
```python
import pandas as pd
import json

# Load results
with open('test_results.jsonl', 'r') as f:
    results = [json.loads(line) for line in f]

df = pd.DataFrame(results)

# Add success column (error is null)
df['success'] = df['error'].isnull()

# Average processing time by model
print(df.groupby('model_name')['processing_time_ms'].mean())

# Success rate by prompt
print(df.groupby('prompt_id')['success'].mean())
```

## Features

- ✓ Automatic file detection
- ✓ Duplicate prevention (uses file modification timestamp)
- ✓ Sequential processing (prevents memory overload)
- ✓ Detailed console logging
- ✓ JSON-lines result format
- ✓ Error handling (continues on failure)
- ✓ Processing time tracking
- ✓ Configurable model+prompt combinations

## Notes

- Files are only re-processed if their modification timestamp changes
- The system runs in the background while the app is open
- Test files and results are excluded from version control (.gitignore)
- Backend must be running (Python API on port 5000)
- Ollama must be running with required models installed
