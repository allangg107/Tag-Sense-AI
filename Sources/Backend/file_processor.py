import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
import logging
import base64

# Text extraction libraries
import docx  # python-docx for Word docs
import PyPDF2  # for PDFs

# Image processing
from PIL import Image  # Pillow for image processing

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileProcessor:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        # Text file extensions
        self.text_extensions = {
            '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
            '.docx', '.pdf'
        }
        # Image file extensions
        self.image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'
        }
        # All supported extensions
        self.supported_extensions = self.text_extensions | self.image_extensions
    
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
    
    def is_image_file(self, file_path: str) -> bool:
        """Check if file is an image"""
        extension = Path(file_path).suffix.lower()
        return extension in self.image_extensions
    
    def _encode_image_to_base64(self, file_path: str) -> str:
        """Encode image file to base64 string"""
        try:
            logger.info(f"Starting image encoding for {file_path}")
            
            # Open and potentially resize image if it's too large
            with Image.open(file_path) as img:
                logger.info(f"Original image mode: {img.mode}, size: {img.width}x{img.height}")
                
                # Convert to RGB if necessary (for PNG with transparency, etc.)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                    logger.info("Converted image to RGB")
                
                # Resize to a very small size for faster processing
                max_size = 256  # Even smaller
                original_size = (img.width, img.height)
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    logger.info(f"Resized image from {original_size} to {img.width}x{img.height}")
                else:
                    logger.info(f"Image size {original_size} is within limits")
                
                # Save to bytes and encode to base64 (very low quality for speed)
                import io
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=50)
                image_bytes = buffer.getvalue()
                
                base64_str = base64.b64encode(image_bytes).decode('utf-8')
                logger.info(f"Encoded image to base64, size: {len(base64_str)} characters")
                
                return base64_str
                
        except Exception as e:
            logger.error(f"Error encoding image {file_path}: {e}")
            return None
    
    def generate_image_tags(self, file_path: str, filename: str) -> List[str]:
        """Generate tags for images using Llama 3.2 Vision"""
        try:
            logger.info(f"Starting image tag generation for {filename}")
            
            # Try method 1: Using smaller base64 encoded image
            image_base64 = self._encode_image_to_base64(file_path)
            if not image_base64:
                logger.error("Failed to encode image to base64")
                return []
            
            # Keep the prompt very simple and strict
            prompt = "List only 5 tags for this image. Tags only, no sentences. Example: dog, park, running, outdoor, happy"

            payload = {
                "model": "llama3.2-vision:11b",
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {
                    "temperature": 0.0,  # Most deterministic
                    "num_predict": 30    # Very short response
                }
            }
            
            logger.info(f"Sending image request to Ollama")
            logger.info(f"Model: {payload['model']}")
            logger.info(f"Prompt: {prompt}")
            logger.info(f"Image base64 size: {len(image_base64)} characters")
            
            # Try the request with a reasonable timeout
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=180)
            
            logger.info(f"Ollama response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                raw_tags = result.get("response", "").strip()
                logger.info(f"Raw response from vision model: '{raw_tags}'")
                
                if not raw_tags:
                    logger.warning("Empty response from vision model")
                    return []
                
                # Parse the response - split by commas and newlines, filter out sentences
                all_text = raw_tags.replace('\n', ', ').replace('.', ',')
                potential_tags = [tag.strip().lower() for tag in all_text.split(',') if tag.strip()]
                
                # Filter to keep only actual tags (single words or short phrases, no sentences)
                tags = []
                for tag in potential_tags:
                    # Skip if it's clearly a sentence (contains "the", "is", "a", etc. or is too long)
                    sentence_words = {'the', 'is', 'are', 'was', 'were', 'a', 'an', 'this', 'that', 'image', 'shows', 'depicts'}
                    words_in_tag = tag.split()
                    
                    # Skip if it contains sentence indicators or is too long
                    if (len(words_in_tag) > 3 or 
                        any(word in sentence_words for word in words_in_tag) or
                        len(tag) > 20):
                        continue
                    
                    # Keep valid tags
                    if len(tag) > 1 and tag.isalpha() or (len(words_in_tag) <= 2):
                        tags.append(tag)
                
                # Remove common unwanted words
                unwanted = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                clean_tags = [tag for tag in tags if tag not in unwanted]
                
                logger.info(f"Final cleaned tags: {clean_tags}")
                return clean_tags[:6]  # Limit to 6 tags
            else:
                logger.error(f"Ollama Vision API error: {response.status_code}")
                logger.error(f"Response text: {response.text}")
                return []
                
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout waiting for Ollama Vision response: {e}")
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error with Ollama Vision: {e}")
            return []
        except Exception as e:
            logger.error(f"Error generating image tags: {e}")
            logger.exception("Full traceback:")
            return []
    
    def _parse_tags_response(self, raw_tags: str) -> List[str]:
        """Parse and clean tags response from any model"""
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
        prompt_words = {'tags', 'content', 'file', 'comma-separated', 'analyze', 'suggest', 'relevant', 'based', 'generate', 'return', 'list', 'image', 'visible', 'focus'}
        
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
        
        return final_tags[:8]  # Limit to 8 tags max
    
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
                
                # Use the shared tag parsing method
                final_tags = self._parse_tags_response(raw_tags)
                logger.info(f"Final cleaned tags: {final_tags}")
                return final_tags
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error("Timeout waiting for Ollama response")
            return []
        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            return []
    
    def get_supported_files_in_folder(self, folder_path):
        """Get list of all supported files in a folder"""
        supported_files = []
        
        try:
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                
                # Skip directories
                if os.path.isdir(file_path):
                    continue
                
                # Check if file extension is supported
                _, ext = os.path.splitext(filename.lower())
                
                if ext in self.text_extensions or ext in self.image_extensions:
                    supported_files.append(file_path)
            
            # Sort files for consistent ordering
            supported_files.sort()
            return supported_files
            
        except Exception as e:
            raise Exception(f"Error scanning folder: {str(e)}")
    
    def process_folder(self, folder_path: str) -> Dict:
        """Process all supported files in a folder and return results"""
        import os
        from pathlib import Path
        
        results = []
        total_files = 0
        processed_files = 0
        errors = 0
        
        logger.info(f"Starting folder processing: {folder_path}")
        
        try:
            # Get all files in the folder
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                return {
                    "success": False,
                    "error": "Folder not found or not a directory",
                    "results": [],
                    "summary": {"total": 0, "processed": 0, "errors": 0}
                }
            
            # Find all supported files
            all_files = []
            for file_path in folder.iterdir():
                if file_path.is_file():
                    extension = file_path.suffix.lower()
                    if extension in self.supported_extensions:
                        all_files.append(str(file_path))
            
            total_files = len(all_files)
            logger.info(f"Found {total_files} supported files in folder")
            
            if total_files == 0:
                return {
                    "success": True,
                    "error": None,
                    "results": [],
                    "summary": {"total": 0, "processed": 0, "errors": 0},
                    "message": "No supported files found in folder"
                }
            
            # Process each file
            for file_path in all_files:
                try:
                    logger.info(f"Processing file {processed_files + 1}/{total_files}: {file_path}")
                    result = self.process_file(file_path)
                    results.append(result)
                    
                    if result["success"]:
                        processed_files += 1
                    else:
                        errors += 1
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    errors += 1
                    results.append({
                        "filename": os.path.basename(file_path),
                        "path": file_path,
                        "success": False,
                        "error": f"Processing error: {str(e)}",
                        "tags": [],
                        "file_type": "unknown"
                    })
            
            return {
                "success": True,
                "error": None,
                "results": results,
                "summary": {
                    "total": total_files,
                    "processed": processed_files,
                    "errors": errors
                },
                "folder_path": folder_path
            }
            
        except Exception as e:
            logger.error(f"Error processing folder {folder_path}: {e}")
            return {
                "success": False,
                "error": f"Folder processing error: {str(e)}",
                "results": [],
                "summary": {"total": 0, "processed": 0, "errors": 0}
            }

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
                "tags": [],
                "file_type": "unknown"
            }
        
        # Determine if this is an image or text file
        if self.is_image_file(file_path):
            # Process image file with Vision model
            logger.info(f"Processing image file: {filename}")
            tags = self.generate_image_tags(file_path, filename)
            
            if not tags:
                # Fallback: generate generic image tags based on filename and type
                extension = Path(file_path).suffix.lower()
                generic_tags = ["image", "photo", "picture"]
                if extension in ['.jpg', '.jpeg']:
                    generic_tags.append("jpeg")
                elif extension == '.png':
                    generic_tags.append("png")
                elif extension == '.gif':
                    generic_tags.extend(["gif", "animation"])
                
                return {
                    "filename": filename,
                    "path": file_path,
                    "success": True,
                    "error": "Vision model timed out. Generated basic tags from file type.",
                    "tags": generic_tags,
                    "file_type": "image",
                    "model_used": "fallback"
                }
            
            return {
                "filename": filename,
                "path": file_path,
                "success": True,
                "error": None,
                "tags": tags,
                "file_type": "image",
                "model_used": "llama3.2-vision:11b"
            }
        else:
            # Process text file with TinyLlama
            logger.info(f"Processing text file: {filename}")
            
            # Extract text
            text = self.extract_text(file_path)
            if not text:
                return {
                    "filename": filename,
                    "path": file_path,
                    "success": False,
                    "error": "Could not extract text from file",
                    "tags": [],
                    "file_type": "text"
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
                "file_type": "text",
                "model_used": "tinyllama",
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