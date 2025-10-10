// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// Check if Ollama server is running
#[tauri::command]
async fn check_ollama_status() -> Result<bool, String> {
    let client = reqwest::Client::new();
    
    match client
        .get("http://localhost:11434/api/tags")
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
    {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

// Send prompt to TinyLlama and get response
#[tauri::command]
async fn send_prompt_to_tinyllama(prompt: String) -> Result<String, String> {
    let client = reqwest::Client::new();
    
    // Create proper JSON payload
    let payload = serde_json::json!({
        "model": "tinyllama",
        "prompt": prompt,
        "stream": false
    });
    
    match client
        .post("http://localhost:11434/api/generate")
        .json(&payload)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                match response.json::<serde_json::Value>().await {
                    Ok(json) => {
                        if let Some(response_text) = json.get("response").and_then(|r| r.as_str()) {
                            Ok(response_text.to_string())
                        } else {
                            Err("No response received from TinyLlama".to_string())
                        }
                    }
                    Err(e) => Err(format!("Failed to parse response: {}", e)),
                }
            } else {
                Err(format!("HTTP error: {}", response.status()))
            }
        }
        Err(e) => Err(format!("Request failed: {}", e)),
    }
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            check_ollama_status,
            send_prompt_to_tinyllama
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}