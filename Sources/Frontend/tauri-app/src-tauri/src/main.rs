// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::UNIX_EPOCH;
use notify::{Watcher, RecursiveMode, EventKind};
use chrono::Utc;

#[derive(Serialize, Deserialize)]
struct TagResponse {
    success: bool,
    tags: Vec<String>,
    error: Option<String>,
    file_type: Option<String>,
    model_used: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct FolderResponse {
    success: bool,
    error: Option<String>,
    results: Vec<serde_json::Value>,
    summary: serde_json::Value,
    folder_path: Option<String>,
    message: Option<String>,
}

// Check if Python backend is running
#[derive(serde::Serialize)]
struct BackendStatus {
    backend_connected: bool,
    ollama_connected: bool,
    error_message: Option<String>,
}

#[tauri::command]
async fn check_backend_status() -> Result<BackendStatus, String> {
    let client = reqwest::Client::new();
    
    match client
        .get("http://127.0.0.1:5000/api/health")
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                match response.json::<serde_json::Value>().await {
                    Ok(json) => {
                        let ollama_connected = json.get("ollama_connected")
                            .and_then(|v| v.as_bool())
                            .unwrap_or(false);
                        
                        let error_message = if !ollama_connected {
                            Some("Ollama is not running. Please start Ollama and try again.".to_string())
                        } else {
                            None
                        };
                        
                        Ok(BackendStatus {
                            backend_connected: true,
                            ollama_connected,
                            error_message,
                        })
                    }
                    Err(_) => Ok(BackendStatus {
                        backend_connected: false,
                        ollama_connected: false,
                        error_message: Some("Backend responded but returned invalid data.".to_string()),
                    })
                }
            } else {
                Ok(BackendStatus {
                    backend_connected: false,
                    ollama_connected: false,
                    error_message: Some(format!("Backend error: {}", response.status())),
                })
            }
        }
        Err(_) => Ok(BackendStatus {
            backend_connected: false,
            ollama_connected: false,
            error_message: Some("Cannot connect to backend. Make sure the Python API is running.".to_string()),
        }),
    }
}

// Get list of supported files in a folder
#[tauri::command]
async fn get_folder_files(folder_path: String) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    
    // Prepare the request payload
    let payload = serde_json::json!({
        "folder_path": folder_path
    });
    
    match client
        .post("http://127.0.0.1:5000/api/get-folder-files")
        .json(&payload)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                match response.json::<serde_json::Value>().await {
                    Ok(json) => Ok(json),
                    Err(e) => Err(format!("Failed to parse response: {}", e)),
                }
            } else {
                Err(format!("Backend error: {}", response.status()))
            }
        }
        Err(e) => Err(format!("Request failed: {}", e)),
    }
}

// Process folder for tag generation
#[tauri::command]
async fn process_folder_for_tags(folder_path: String) -> Result<FolderResponse, String> {
    let client = reqwest::Client::new();
    
    // Prepare the request payload
    let payload = serde_json::json!({
        "folder_path": folder_path
    });
    
    match client
        .post("http://127.0.0.1:5000/api/process-folder")
        .json(&payload)
        .timeout(std::time::Duration::from_secs(600)) // 10 minutes for folder processing
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                match response.json::<serde_json::Value>().await {
                    Ok(json) => {
                        let success = json.get("success").and_then(|s| s.as_bool()).unwrap_or(false);
                        let error = json.get("error")
                            .and_then(|e| e.as_str())
                            .map(|s| s.to_string());
                        let results = json.get("results")
                            .and_then(|r| r.as_array())
                            .map(|arr| arr.clone())
                            .unwrap_or_default();
                        let summary = json.get("summary").cloned().unwrap_or(serde_json::Value::Null);
                        let folder_path = json.get("folder_path")
                            .and_then(|f| f.as_str())
                            .map(|s| s.to_string());
                        let message = json.get("message")
                            .and_then(|m| m.as_str())
                            .map(|s| s.to_string());
                        
                        Ok(FolderResponse {
                            success,
                            error,
                            results,
                            summary,
                            folder_path,
                            message,
                        })
                    }
                    Err(e) => Err(format!("Failed to parse response: {}", e)),
                }
            } else {
                Err(format!("Backend error: {}", response.status()))
            }
        }
        Err(e) => Err(format!("Request failed: {}", e)),
    }
}

// Process file for tag generation
#[tauri::command]
async fn process_file_for_tags(file_path: String, context: Option<String>) -> Result<TagResponse, String> {
    let client = reqwest::Client::new();
    
    // Prepare the request payload
    let mut payload = serde_json::json!({
        "file_path": file_path
    });
    
    // Add context if provided
    if let Some(ctx) = context {
        if !ctx.trim().is_empty() {
            payload["context"] = serde_json::Value::String(ctx);
        }
    }
    
    match client
        .post("http://127.0.0.1:5000/api/process-file")
        .json(&payload)
        .timeout(std::time::Duration::from_secs(360)) // 6 minutes timeout for vision model processing
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                match response.json::<serde_json::Value>().await {
                    Ok(json) => {
                        let success = json.get("success").and_then(|s| s.as_bool()).unwrap_or(false);
                        let tags = json.get("tags")
                            .and_then(|t| t.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|v| v.as_str())
                                    .map(|s| s.to_string())
                                    .collect()
                            })
                            .unwrap_or_default();
                        let error = json.get("error")
                            .and_then(|e| e.as_str())
                            .map(|s| s.to_string());
                        let file_type = json.get("file_type")
                            .and_then(|f| f.as_str())
                            .map(|s| s.to_string());
                        let model_used = json.get("model_used")
                            .and_then(|m| m.as_str())
                            .map(|s| s.to_string());
                        
                        Ok(TagResponse {
                            success,
                            tags,
                            error,
                            file_type,
                            model_used,
                        })
                    }
                    Err(e) => Err(format!("Failed to parse response: {}", e)),
                }
            } else {
                Err(format!("Backend error: {}", response.status()))
            }
        }
        Err(e) => Err(format!("Request failed: {}", e)),
    }
}

// Test configuration structures
#[derive(Debug, Clone, Serialize, Deserialize)]
struct TestConfig {
    test_folder: String,
    models: Vec<Model>,
    prompts: Vec<Prompt>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Model {
    id: String,
    name: String,
    file_types: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Prompt {
    id: String,
    prompt: String,
    options: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ModelPromptCombo {
    id: String,
    model: String,
    file_types: Vec<String>,
    prompt: String,
    options: serde_json::Value,
}

#[derive(Debug, Serialize)]
struct TestResult {
    timestamp: String,
    file_path: String,
    file_modified_time: u64,
    model_name: String,
    prompt_id: String,
    run_number: u32,
    tags: Vec<String>,
    processing_time_ms: f64,
    error: Option<String>,
}

// Shared state for tracking processed files
type ProcessedFilesMap = Arc<Mutex<HashMap<PathBuf, u64>>>;

// Load test configuration
fn load_test_config(_app_handle: &tauri::AppHandle) -> Result<TestConfig, String> {
    // Get the executable path and navigate to project root
    let exe_path = std::env::current_exe()
        .map_err(|e| format!("Failed to get executable path: {}", e))?;
    
    // Navigate up from executable to project root
    // Path is typically: project/Sources/Frontend/tauri-app/src-tauri/target/debug/tag-sense-ai.exe
    let project_root = exe_path
        .parent() // target/debug
        .and_then(|p| p.parent()) // target
        .and_then(|p| p.parent()) // src-tauri
        .and_then(|p| p.parent()) // tauri-app
        .and_then(|p| p.parent()) // Frontend
        .and_then(|p| p.parent()) // Sources
        .and_then(|p| p.parent()) // project root
        .ok_or("Failed to find project root")?;
    
    let config_path = project_root.join("test_config.json");
    
    println!("Loading test config from: {:?}", config_path);
    
    let config_content = std::fs::read_to_string(&config_path)
        .map_err(|e| format!("Failed to read config file: {}", e))?;
    
    let config: TestConfig = serde_json::from_str(&config_content)
        .map_err(|e| format!("Failed to parse config: {}", e))?;
    
    let combination_count = config.models.len() * config.prompts.len();
    println!("Loaded {} models × {} prompts = {} combinations", 
             config.models.len(), config.prompts.len(), combination_count);
    
    Ok(config)
}

// Write test result to JSON-lines file
fn write_test_result(result: &TestResult, _app_handle: &tauri::AppHandle) -> Result<(), String> {
    // Get the executable path and navigate to project root
    let exe_path = std::env::current_exe()
        .map_err(|e| format!("Failed to get executable path: {}", e))?;
    
    let project_root = exe_path
        .parent()
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .ok_or("Failed to find project root")?;
    
    let results_path = project_root.join("test_results.jsonl");
    
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&results_path)
        .map_err(|e| format!("Failed to open results file: {}", e))?;
    
    let json_line = serde_json::to_string(result)
        .map_err(|e| format!("Failed to serialize result: {}", e))?;
    
    writeln!(file, "{}", json_line)
        .map_err(|e| format!("Failed to write result: {}", e))?;
    
    Ok(())
}

// Warmup a model with a simple prompt (not logged to results)
async fn warmup_model(file_path: &PathBuf, model_name: &str) {
    println!("  ⚙ Warming up model: {}", model_name);
    
    let client = reqwest::Client::new();
    let payload = serde_json::json!({
        "file_path": file_path.to_str().unwrap(),
        "model": model_name,
        "prompt_template": "Tag: {text}\\n\\nTag:",
        "options": {"temperature": 0.0, "num_predict": 5}
    });
    
    match client
        .post("http://127.0.0.1:5000/api/process-file")
        .json(&payload)
        .timeout(std::time::Duration::from_secs(120))
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                println!("  ✓ Model warmed up");
            } else {
                eprintln!("  ⚠ Warmup returned HTTP {}", response.status());
            }
        }
        Err(e) => {
            eprintln!("  ⚠ Warmup failed: {}", e);
        }
    }
}

// Process a file with all model+prompt combinations
async fn process_file_with_all_combos(
    file_path: PathBuf,
    config: &TestConfig,
    app_handle: tauri::AppHandle,
) -> Result<(), String> {
    println!("\n========================================");
    println!("Processing file: {:?}", file_path);
    println!("========================================");
    
    // Get file metadata
    let metadata = std::fs::metadata(&file_path)
        .map_err(|e| format!("Failed to get file metadata: {}", e))?;
    
    let modified_time = metadata.modified()
        .map_err(|e| format!("Failed to get modified time: {}", e))?
        .duration_since(UNIX_EPOCH)
        .map_err(|e| format!("Failed to convert time: {}", e))?
        .as_secs();
    
    // Determine file type
    let extension = file_path.extension()
        .and_then(|e| e.to_str())
        .unwrap_or("");
    
    let file_type = if matches!(extension, "jpg" | "jpeg" | "png" | "gif" | "bmp" | "webp" | "tiff" | "tif") {
        "image"
    } else {
        "text"
    };
    
    // Generate all model+prompt combinations
    let mut combinations = Vec::new();
    for model in &config.models {
        // Only include models that support this file type
        if !model.file_types.contains(&file_type.to_string()) {
            continue;
        }
        
        for prompt in &config.prompts {
            combinations.push(ModelPromptCombo {
                id: format!("{}_{}", model.id, prompt.id),
                model: model.name.clone(),
                file_types: model.file_types.clone(),
                prompt: prompt.prompt.clone(),
                options: prompt.options.clone(),
            });
        }
    }
    
    println!("Found {} applicable model+prompt combinations for {} file", 
             combinations.len(), file_type);
    
    // Warmup phase: run each unique model once with a dud prompt
    let unique_models: std::collections::HashSet<_> = config.models.iter()
        .filter(|m| m.file_types.contains(&file_type.to_string()))
        .map(|m| m.name.as_str())
        .collect();
    
    if !unique_models.is_empty() {
        println!("\n--- Warmup Phase: {} model(s) ---", unique_models.len());
        for model in unique_models {
            warmup_model(&file_path, model).await;
        }
        println!("--- Warmup Complete ---\n");
    }
    
    println!("Running each combination 2 times for consistency testing");
    
    let total_runs = combinations.len() * 2;
    let mut run_count = 0;
    
    // Process with each combination sequentially, twice
    for combo in combinations.iter() {
        for run_number in 1..=2 {
            run_count += 1;
            println!("\n[{}/{}] Testing: {} (model: {}) - Run {}", 
                     run_count, total_runs, combo.id, combo.model, run_number);
        
        // Call backend API
        let client = reqwest::Client::new();
        let payload = serde_json::json!({
            "file_path": file_path.to_str().unwrap(),
            "model": combo.model,
            "prompt_template": combo.prompt,
            "options": combo.options,
        });
        
        let start_time = std::time::Instant::now();
        
        match client
            .post("http://127.0.0.1:5000/api/process-file")
            .json(&payload)
            .timeout(std::time::Duration::from_secs(360))
            .send()
            .await
        {
            Ok(response) => {
                let elapsed = start_time.elapsed().as_secs_f64() * 1000.0;
                
                if response.status().is_success() {
                    match response.json::<serde_json::Value>().await {
                        Ok(json) => {
                            let tags: Vec<String> = json.get("tags")
                                .and_then(|t| t.as_array())
                                .map(|arr| {
                                    arr.iter()
                                        .filter_map(|v| v.as_str())
                                        .map(|s| s.to_string())
                                        .collect()
                                })
                                .unwrap_or_default();
                            
                            let processing_time = json.get("processing_time_ms")
                                .and_then(|t| t.as_f64())
                                .unwrap_or(elapsed);
                            
                            let error = json.get("error")
                                .and_then(|e| e.as_str())
                                .map(|s| s.to_string());
                            
                            println!("  ✓ Success: {} tags in {:.2}ms", tags.len(), processing_time);
                            println!("  Tags: {:?}", tags);
                            
                            let result = TestResult {
                                timestamp: Utc::now().to_rfc3339(),
                                file_path: file_path.to_str().unwrap().to_string(),
                                file_modified_time: modified_time,
                                model_name: combo.model.clone(),
                                prompt_id: combo.id.clone(),
                                run_number,
                                tags,
                                processing_time_ms: processing_time,
                                error,
                            };
                            
                            if let Err(e) = write_test_result(&result, &app_handle) {
                                eprintln!("  ⚠ Failed to write result: {}", e);
                            }
                        }
                        Err(e) => {
                            eprintln!("  ✗ Failed to parse response: {}", e);
                            
                            let result = TestResult {
                                timestamp: Utc::now().to_rfc3339(),
                                file_path: file_path.to_str().unwrap().to_string(),
                                file_modified_time: modified_time,
                                model_name: combo.model.clone(),
                                prompt_id: combo.id.clone(),
                                run_number,
                                tags: vec![],
                                processing_time_ms: elapsed,
                                error: Some(format!("Parse error: {}", e)),
                            };
                            
                            let _ = write_test_result(&result, &app_handle);
                        }
                    }
                } else {
                    eprintln!("  ✗ Backend error: {}", response.status());
                    
                    let result = TestResult {
                        timestamp: Utc::now().to_rfc3339(),
                        file_path: file_path.to_str().unwrap().to_string(),
                        file_modified_time: modified_time,
                        model_name: combo.model.clone(),
                        prompt_id: combo.id.clone(),
                        run_number,
                        tags: vec![],
                        processing_time_ms: elapsed,
                        error: Some(format!("HTTP {}", response.status())),
                    };
                    
                    let _ = write_test_result(&result, &app_handle);
                }
            }
            Err(e) => {
                let elapsed = start_time.elapsed().as_secs_f64() * 1000.0;
                eprintln!("  ✗ Request failed: {}", e);
                
                let result = TestResult {
                    timestamp: Utc::now().to_rfc3339(),
                    file_path: file_path.to_str().unwrap().to_string(),
                    file_modified_time: modified_time,
                    model_name: combo.model.clone(),
                    prompt_id: combo.id.clone(),
                    run_number,
                    tags: vec![],
                    processing_time_ms: elapsed,
                    error: Some(format!("Request error: {}", e)),
                };
                
                let _ = write_test_result(&result, &app_handle);
            }
            }
        }
    }
    
    println!("\n✓ Completed processing file: {:?}", file_path);
    
    Ok(())
}

// Start the file watcher
fn start_file_watcher(app_handle: tauri::AppHandle) {
    tauri::async_runtime::spawn(async move {
        println!("Starting file watcher...");
        
        // Load configuration
        let config = match load_test_config(&app_handle) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("Failed to load test config: {}", e);
                return;
            }
        };
        
        // Get test folder path using executable path
        let exe_path = match std::env::current_exe() {
            Ok(p) => p,
            Err(e) => {
                eprintln!("Failed to get executable path: {}", e);
                return;
            }
        };
        
        let project_root = match exe_path
            .parent()
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
        {
            Some(r) => r,
            None => {
                eprintln!("Failed to find project root");
                return;
            }
        };
        
        let test_folder = project_root.join(&config.test_folder);
        
        if !test_folder.exists() {
            eprintln!("Test folder does not exist: {:?}", test_folder);
            return;
        }
        
        println!("Monitoring folder: {:?}", test_folder);
        
        // Track processed files with their modification times
        let processed_files: ProcessedFilesMap = Arc::new(Mutex::new(HashMap::new()));
        
        // Set up file watcher
        let (tx, rx) = std::sync::mpsc::channel();
        
        let mut watcher = match notify::recommended_watcher(tx) {
            Ok(w) => w,
            Err(e) => {
                eprintln!("Failed to create watcher: {}", e);
                return;
            }
        };
        
        if let Err(e) = watcher.watch(&test_folder, RecursiveMode::Recursive) {
            eprintln!("Failed to watch folder: {}", e);
            return;
        }
        
        println!("✓ File watcher initialized successfully");
        
        // Process events
        loop {
            match rx.recv() {
                Ok(Ok(event)) => {
                    // Handle create and modify events
                    if matches!(event.kind, EventKind::Create(_) | EventKind::Modify(_)) {
                        for path in event.paths {
                            if path.is_file() {
                                // Check if it's a supported file type
                                if let Some(ext) = path.extension() {
                                    let ext_str = ext.to_str().unwrap_or("");
                                    let supported = matches!(
                                        ext_str,
                                        "txt" | "md" | "py" | "js" | "html" | "css" | "json" | "xml" | 
                                        "docx" | "pdf" | "jpg" | "jpeg" | "png" | "gif" | "bmp" | 
                                        "webp" | "tiff" | "tif"
                                    );
                                    
                                    if supported {
                                        // Check if we've already processed this file with this modification time
                                        if let Ok(metadata) = std::fs::metadata(&path) {
                                            if let Ok(modified) = metadata.modified() {
                                                let modified_secs = modified
                                                    .duration_since(UNIX_EPOCH)
                                                    .unwrap_or_default()
                                                    .as_secs();
                                                
                                                let mut processed = processed_files.lock().unwrap();
                                                
                                                let should_process = match processed.get(&path) {
                                                    Some(&last_modified) => last_modified != modified_secs,
                                                    None => true,
                                                };
                                                
                                                if should_process {
                                                    println!("\n→ New/modified file detected: {:?}", path);
                                                    processed.insert(path.clone(), modified_secs);
                                                    drop(processed); // Release lock before async operation
                                                    
                                                    // Process the file
                                                    let path_clone = path.clone();
                                                    let config_clone = config.clone();
                                                    let app_handle_clone = app_handle.clone();
                                                    
                                                    tauri::async_runtime::spawn(async move {
                                                        if let Err(e) = process_file_with_all_combos(
                                                            path_clone,
                                                            &config_clone,
                                                            app_handle_clone,
                                                        ).await {
                                                            eprintln!("Error processing file: {}", e);
                                                        }
                                                    });
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Ok(Err(e)) => eprintln!("Watch error: {}", e),
                Err(e) => {
                    eprintln!("Channel error: {}", e);
                    break;
                }
            }
        }
    });
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Start the file watcher
            let handle = app.handle();
            start_file_watcher(handle);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            check_backend_status,
            process_file_for_tags,
            process_folder_for_tags,
            get_folder_files
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}