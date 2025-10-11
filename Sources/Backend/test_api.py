import requests
import json

# Test the Tag Sense AI API
API_BASE = "http://127.0.0.1:5000/api"

def test_health():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_supported_types():
    """Test the supported types endpoint"""
    print("📋 Testing supported types endpoint...")
    response = requests.get(f"{API_BASE}/supported-types")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_process_file():
    """Test processing a single file"""
    print("🏷️  Testing file processing...")
    file_path = r"C:\Users\Allan\OneDrive\Programming\Tag-Sense-AI\Sources\Backend\test_sample.txt"
    
    data = {"file_path": file_path}
    response = requests.post(f"{API_BASE}/process-file", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

if __name__ == "__main__":
    print("🧪 Testing Tag Sense AI API")
    print("=" * 40)
    
    try:
        test_health()
        test_supported_types()
        test_process_file()
        print("✅ All tests completed!")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Make sure it's running on port 5000.")
    except Exception as e:
        print(f"❌ Test failed: {e}")