// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};

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

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            check_backend_status,
            process_file_for_tags,
            process_folder_for_tags,
            get_folder_files
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}