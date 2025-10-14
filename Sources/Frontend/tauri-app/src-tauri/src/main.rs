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

// Check if Python backend is running
#[tauri::command]
async fn check_backend_status() -> Result<bool, String> {
    let client = reqwest::Client::new();
    
    match client
        .get("http://127.0.0.1:5000/api/health")
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
    {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
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
            process_file_for_tags
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}