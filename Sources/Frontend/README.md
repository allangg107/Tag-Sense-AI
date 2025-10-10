# Tag Sense AI - Tauri Frontend

A simple desktop app built with React + Tauri to interface with TinyLlama through Ollama.

## Prerequisites

1. **Node.js** (v16 or later)
2. **Rust** (latest stable version)
3. **Ollama** with TinyLlama installed (you already have this ✅)

## Setup Instructions

### 1. Install Rust (if not already installed)
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
cd "C:\Users\Allan\OneDrive\Programming\Tag-Sense-AI\Sources\Frontend\tauri-app"
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

## Features

- ✅ Simple, clean UI
- ✅ Text input box for prompts
- ✅ Send button to submit requests
- ✅ Response display area
- ✅ Connection status indicator
- ✅ Keyboard shortcut (Ctrl+Enter to send)
- ✅ Loading states and error handling

## How it Works

1. **Frontend (React)**: Provides the user interface
2. **Backend (Rust/Tauri)**: Handles HTTP requests to Ollama
3. **Ollama**: Serves the TinyLlama model

The app communicates with your existing Ollama installation on `localhost:11434`.

## Usage

1. Make sure Ollama is running (it should be, since your Python script worked)
2. Start the app with `npm run tauri dev`
3. Type your message in the text box
4. Click "Send to TinyLlama" or press Ctrl+Enter
5. View the response below

## Troubleshooting

- **"Ollama not available"**: Make sure Ollama is running (`ollama serve`)
- **Build errors**: Ensure Rust is properly installed
- **Port conflicts**: The app uses port 1420 for development

This replaces your terminal interface with a proper desktop GUI!