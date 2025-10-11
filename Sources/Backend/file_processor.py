import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Text extraction libraries
import docx  # python-docx for Word docs
import PyPDF2  # for PDFs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileProcessor:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.supported_extensions = {
            '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
            '.docx', '.pdf'
        }
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """Extract text from various file types"""
        try:
            path = Path(file_path)
            extension = path.suffix.lower()
            
            if extension == '.txt' or extension == '.md':
                return self._extract_plain_text(file_path)
            elif extension == '.docx':
                return self._extract_docx(file_path)
            elif extension == '.pdf':
                return self._extract_pdf(file_path)
            elif extension in {'.py', '.js', '.html', '.css', '.json', '.xml'}:
                return self._extract_plain_text(file_path)
            else:
                # For other formats, try plain text extraction
                return self._extract_plain_text(file_path)
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return None
    
    def _extract_plain_text(self, file_path: str) -> str:
        """Extract text from plain text files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    
    def _extract_docx(self, file_path: str) -> str:
        """Extract text from Word documents"""
        doc = docx.Document(file_path)
        text_parts = []
        for paragraph in doc.paragraphs:
            text_parts.append(paragraph.text)
        return '\n'.join(text_parts)
    
    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF files"""
        text_parts = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())
        return '\n'.join(text_parts)
    
    def generate_tags(self, text: str, filename: str) -> List[str]:
        """Generate tags using TinyLlama"""
        try:
            # Truncate text if too long (TinyLlama has context limits)
            max_chars = 1500
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            prompt = f"""Based on this content, generate relevant tags. Return only the tags as a comma-separated list.

Content: {text}

Tags:"""

            payload = {
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 50
                }
            }
            
            logger.info(f"Sending request to Ollama: {self.ollama_url}/api/generate")
            logger.info(f"Model: {payload['model']}")
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30)
            
            logger.info(f"Ollama response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Ollama response: {result}")
                
                raw_tags = result.get("response", "").strip()
                logger.info(f"Raw tags from model: '{raw_tags}'")
                
                if not raw_tags:
                    logger.warning("Empty response from model")
                    return []
                
                # Split on newlines first to handle numbered lists, then on commas
                lines = raw_tags.split('\n')
                all_tags = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Remove "Tags:" prefix if present
                    if line.lower().startswith('tags:'):
                        line = line[5:].strip()
                    
                    # Remove numbered list prefixes (e.g., "1. ", "2. ", etc.)
                    import re
                    line = re.sub(r'^\d+\.\s*', '', line)
                    
                    # Split by commas and clean each tag
                    tags_in_line = [tag.strip() for tag in line.split(',') if tag.strip()]
                    all_tags.extend(tags_in_line)
                
                # Clean and validate tags
                cleaned_tags = []
                # Filter out prompt-related words that might leak through
                prompt_words = {'tags', 'content', 'file', 'comma-separated', 'analyze', 'suggest', 'relevant', 'based', 'generate', 'return', 'list'}
                
                for tag in all_tags:
                    # Remove quotes, periods, and clean up
                    tag = tag.strip('."\'').lower()
                    tag = tag.strip()
                    
                    # Skip pure numbers, very short/long tags, or prompt-related words
                    if (tag and len(tag) > 1 and len(tag) < 30 and 
                        not tag.isdigit() and 
                        tag not in prompt_words):
                        cleaned_tags.append(tag)
                
                # Remove duplicates while preserving order
                seen = set()
                final_tags = []
                for tag in cleaned_tags:
                    if tag not in seen:
                        seen.add(tag)
                        final_tags.append(tag)
                
                logger.info(f"Final cleaned tags: {final_tags}")
                return final_tags[:8]  # Limit to 8 tags max
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error("Timeout waiting for Ollama response")
            return []
        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            return []
    
    def process_file(self, file_path: str) -> Dict:
        """Process a single file and return results"""
        filename = os.path.basename(file_path)
        
        # Check if file type is supported
        extension = Path(file_path).suffix.lower()
        if extension not in self.supported_extensions:
            return {
                "filename": filename,
                "path": file_path,
                "success": False,
                "error": f"Unsupported file type: {extension}",
                "tags": []
            }
        
        # Extract text
        text = self.extract_text(file_path)
        if not text:
            return {
                "filename": filename,
                "path": file_path,
                "success": False,
                "error": "Could not extract text from file",
                "tags": []
            }
        
        logger.info(f"Extracted {len(text)} characters from {filename}")
        
        # Generate tags
        tags = self.generate_tags(text, filename)
        
        return {
            "filename": filename,
            "path": file_path,
            "success": True,
            "error": None,
            "tags": tags,
            "text_preview": text[:200] + "..." if len(text) > 200 else text
        }

def main():
    """Test the file processor"""
    processor = FileProcessor()
    
    # Test with a sample file
    test_file = input("Enter path to a text file to test: ").strip('"')
    
    if not os.path.exists(test_file):
        print(f"File not found: {test_file}")
        return
    
    print(f"Processing: {test_file}")
    result = processor.process_file(test_file)
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()