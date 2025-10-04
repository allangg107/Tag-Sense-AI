# Tag-Sense-AI
Auto-tag files based on suggested tags using AI.

# Current Approach (WIP)
1) User Interaction (React + Tauri)
- User selects files and clicks “Auto Tag My Files.”
- Tauri backend (Rust) receives the event and launches the Python script (via sidecar or API call).

2) AI Tagging (Python Backend)
- Python analyzes file content (text, images, metadata).
- A local AI model (e.g., transformer for text, CNN for images) generates suggested tags.
- Tags are stored in a shared location (e.g., SQLite DB, JSON file, or REST endpoint).

3) User Review (React UI)
- Suggested tags are displayed in the UI.
- User can accept, reject, or edit them.

4) Native Tagging (C++ COM DLL)
- Upon acceptance, Tauri or Python triggers the C++ layer.
- C++ reads the stored tags and applies them via Windows Explorer Property Handler.
