# Tag Sense AI

Desktop app to interface with an LLM in order to generate suggested tags for files.

<img width="1918" height="1078" alt="image" src="https://github.com/user-attachments/assets/69744d0c-b94a-4d95-b659-1b38a4c3323e" />

## Prerequisites

1. **Node.js** (v16 or later)
2. **Rust** (latest stable version)
3. **Ollama** with TinyLlama installed

## Setup Instructions

### 1. Install Rust
```bash
# Windows - download from https://rustup.rs/ or use:
winget install Rustlang.Rustup
```

### 2. Install Tauri CLI
```bash
npm install -g @tauri-apps/cli
```

### 3. Install Dependencies
```bash
cd "\Tag-Sense-AI\Sources\Frontend\tauri-app"
npm install
```

### 4. Run the App

#### Development Mode:
```bash
npm run tauri dev
```

#### Build for Production:
```bash
npm run tauri build
```

## How it Works

1. **Frontend (React)**: Provides the user interface
2. **Backend (Rust/Tauri)**: Handles HTTP requests to Ollama
3. **Ollama**: Serves the TinyLlama model

The app communicates with your existing Ollama installation on `localhost:11434`.

## Usage

1. Make sure Ollama is running
2. Start the app with `npm run tauri dev`
3. Type your message in the text box
4. Click "Generate Tags" or press Ctrl+Enter
5. View the response below

## Troubleshooting

- **"Ollama not available"**: Make sure Ollama is running (`ollama serve`)
- **Build errors**: Ensure Rust is properly installed
- **Port conflicts**: The app uses port 1420 for development
