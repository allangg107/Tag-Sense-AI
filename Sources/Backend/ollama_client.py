"""
Simple TinyLlama Interface - Hello World Example
Basic script to test TinyLlama installation with Ollama
"""

import requests
import json
import time
from typing import List, Dict, Optional, Tuple


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    def is_ollama_running(self) -> bool:
        """Checks if the Ollama server is responsive."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=1)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def generate_tags(self, model: str, prompt: str, options: Dict,
                      images: Optional[List[str]] = None) -> Tuple[List[str], float]:
        """
        Generates tags for a given prompt, model, and optional images.
        Returns a tuple of (tags_list, processing_time_ms).
        """
        start_time = time.perf_counter()

        payload = {
            "model": model,
            "prompt": prompt,
            "options": options,
            "stream": False
        }
        if images:
            payload["images"] = images

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=360  # Generous timeout for large models
            )
            response.raise_for_status()  # Raise an exception for bad status codes

            result = response.json()
            raw_response = result.get("response", "").strip()

            # Simple parsing: split by comma and newline, then clean up
            tags = [
                tag.strip().lower()
                for tag in raw_response.replace('\n', ',').split(',')
                if tag.strip()
            ]

            processing_time = (time.perf_counter() - start_time) * 1000
            return tags, processing_time

        except requests.exceptions.RequestException as e:
            # Re-raise as a more generic exception to be caught by the API layer
            raise RuntimeError(f"Ollama API request failed: {e}")
        except json.JSONDecodeError:
            raise RuntimeError("Failed to decode JSON response from Ollama.")


def main():
    """Simple test of TinyLlama"""
    print("🦙 TinyLlama Hello World Test")
    print("=" * 30)

    client = OllamaClient()

    # Check if Ollama is running
    if not client.is_ollama_running():
        print("❌ Ollama server is not running!")
        print("💡 Start it by running: ollama serve")
        return

    print("✅ Ollama server is running")

    # Test with a simple prompt
    print("\n🔄 Testing TinyLlama with a simple prompt...")
    test_prompt = "Hello! What is 2 + 2?"

    print(f"Prompt: {test_prompt}")
    print("Response: ", end="")

    response, _ = client.generate_tags("tinyllama", test_prompt, {})
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
            response, _ = client.generate_tags("tinyllama", user_input, {})
            print(response)

        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break


if __name__ == "__main__":
    main()