"""
Simple TinyLlama Interface - Hello World Example
Basic script to test TinyLlama installation with Ollama
"""

import requests
import json


def check_ollama():
    """Check if Ollama server is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def ask_tinyllama(prompt):
    """Send a prompt to TinyLlama and get response"""
    data = {
        "model": "tinyllama",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post("http://localhost:11434/api/generate", json=data)
        response.raise_for_status()
        result = response.json()
        return result.get('response', 'No response received')
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"


def main():
    """Simple test of TinyLlama"""
    print("🦙 TinyLlama Hello World Test")
    print("=" * 30)
    
    # Check if Ollama is running
    if not check_ollama():
        print("❌ Ollama server is not running!")
        print("💡 Start it by running: ollama serve")
        return
    
    print("✅ Ollama server is running")
    
    # Test with a simple prompt
    print("\n🔄 Testing TinyLlama with a simple prompt...")
    test_prompt = "Hello! What is 2 + 2?"
    
    print(f"Prompt: {test_prompt}")
    print("Response: ", end="")
    
    response = ask_tinyllama(test_prompt)
    print(response)
    
    # Interactive mode
    print("\n" + "=" * 30)
    print("💬 Interactive mode (type 'quit' to exit)")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if not user_input:
                continue
            
            print("TinyLlama: ", end="")
            response = ask_tinyllama(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break


if __name__ == "__main__":
    main()