import requests
import json

def check_ollama():
    """Debug Ollama connection and available models"""
    
    print("🔍 Debugging Ollama connection...")
    
    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags")
        print(f"✅ Ollama is running (status: {response.status_code})")
        
        if response.status_code == 200:
            models = response.json()
            print(f"📋 Available models: {json.dumps(models, indent=2)}")
            
            # List model names
            if 'models' in models:
                model_names = [model['name'] for model in models['models']]
                print(f"🎯 Model names: {model_names}")
                
                # Check if tinyllama is available
                if any('tinyllama' in name.lower() for name in model_names):
                    print("✅ TinyLlama found!")
                else:
                    print("❌ TinyLlama not found in available models")
                    print("💡 Try running: ollama pull tinyllama")
        
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("💡 Make sure Ollama is running: ollama serve")
        return
    
    # Test a simple generation
    print("\n🧪 Testing simple generation...")
    
    # Get the first available model
    try:
        models_response = requests.get("http://localhost:11434/api/tags")
        if models_response.status_code == 200:
            models_data = models_response.json()
            if models_data.get('models'):
                first_model = models_data['models'][0]['name']
                print(f"🎯 Testing with model: {first_model}")
                
                test_payload = {
                    "model": first_model,
                    "prompt": "Hello! Please respond with just: apple, banana, orange",
                    "stream": False
                }
                
                response = requests.post("http://localhost:11434/api/generate", json=test_payload, timeout=30)
                print(f"Test response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Test response: {json.dumps(result, indent=2)}")
                else:
                    print(f"Test failed: {response.text}")
            
    except Exception as e:
        print(f"Test generation failed: {e}")

if __name__ == "__main__":
    check_ollama()