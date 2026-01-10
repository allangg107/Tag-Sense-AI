import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional, Union
import logging
import base64
import time

# Text extraction libraries
import docx
import PyPDF2
import fitz  # PyMuPDF

# Image processing
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
# If a PDF has fewer than this many characters, it's considered a scan
PDF_TEXT_THRESHOLD = 100 

class FileProcessor:
    def __init__(self):
        # Supported file extensions, now simplified
        self.supported_extensions = {
            '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
            '.docx', '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', 
            '.webp', '.tiff', '.tif'
        }

    def read_file_content(self, file_path: str) -> Optional[Dict[str, Union[str, bytes]]]:
        """
        Reads a file and returns its content and type.
        For PDFs, it dynamically determines if it's text or a scan (image).
        
        Returns:
            A dictionary like {'type': 'text', 'content': '...'} or 
            {'type': 'image', 'content': 'base64...'} or
            {'type': 'image_from_pdf', 'content': 'base64...'}.
            Returns None if the file type is unsupported or an error occurs.
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension not in self.supported_extensions:
            logger.warning(f"Unsupported file type: {extension}")
            return None

        try:
            if extension == '.pdf':
                return self._process_pdf(file_path)
            elif extension in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}:
                return {
                    'type': 'image',
                    'content': self._encode_image_to_base64(file_path)
                }
            elif extension == '.docx':
                return {
                    'type': 'text',
                    'content': self._extract_docx_text(file_path)
                }
            else: # All other supported types are plain text
                return {
                    'type': 'text',
                    'content': self._extract_plain_text(file_path)
                }
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return None

    def _process_pdf(self, file_path: str) -> Dict[str, str]:
        """
        Processes a PDF file, trying to extract text first, then falling back
        to rendering it as an image if it appears to be a scanned document.
        """
        # 1. Attempt to extract text
        text = self._extract_pdf_text(file_path)
        
        # 2. Check if text extraction was successful
        if text and len(text.strip()) > PDF_TEXT_THRESHOLD:
            logger.info(f"PDF is text-based (found {len(text)} chars).")
            return {'type': 'text', 'content': text}
        
        # 3. If not, render the first page as an image
        logger.warning(f"PDF appears to be a scan (found {len(text.strip())} chars). Rendering as image.")
        image_base64 = self._render_pdf_page_to_base64(file_path)
        if image_base64:
            return {'type': 'image_from_pdf', 'content': image_base64}
        
        # 4. If both fail, return an error state (empty text)
        logger.error(f"Failed to extract text or render image for PDF: {file_path}")
        return {'type': 'text', 'content': ''}

    def _extract_plain_text(self, file_path: str) -> str:
        """Extracts text from plain text files."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _extract_docx_text(self, file_path: str) -> str:
        """Extracts text from a .docx file."""
        doc = docx.Document(file_path)
        return '\n'.join([p.text for p in doc.paragraphs])

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extracts text from a PDF using PyPDF2."""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return '\n'.join([page.extract_text() for page in reader.pages])
        except Exception as e:
            logger.error(f"PyPDF2 failed to extract text from {file_path}: {e}")
            return ""

    def _render_pdf_page_to_base64(self, file_path: str, page_num: int = 0) -> Optional[str]:
        """
        Renders a single page of a PDF to a base64 encoded image string.
        """
        try:
            doc = fitz.open(file_path)
            if not doc.page_count:
                logger.error(f"PDF has no pages: {file_path}")
                return None
            
            page = doc.load_page(page_num)
            
            # Render page to a pixmap (image)
            # Increase zoom for higher resolution
            pix = page.get_pixmap(dpi=200)
            
            # Convert pixmap to image bytes (PNG for lossless quality)
            img_bytes = pix.tobytes("png")
            
            return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"PyMuPDF failed to render PDF page {file_path}: {e}")
            return None

    def _encode_image_to_base64(self, file_path: str) -> Optional[str]:
        """Encodes an image file to a base64 string."""
        try:
            with open(file_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image {file_path}: {e}")
            return None

    def _prepare_text_for_model(self, text: str, model_name: str) -> str:
        """
        Truncates text to fit within the model's context window, preserving
        the beginning and end of the document.
        """
        # Simplified logic: use a smaller context for smaller models
        # This can be made more sophisticated later
        max_chars = 3000 if 'tiny' in model_name.lower() else 8000
        
        if len(text) <= max_chars:
            return text
            
        logger.info(f"Truncating text from {len(text)} to {max_chars} chars.")
        
        # Keep the first 40% and the last 60%
        start_len = int(max_chars * 0.4)
        end_len = int(max_chars * 0.6)
        
        start_text = text[:start_len]
        end_text = text[-end_len:]
        
        return f"{start_text}\n\n...[CONTENT TRUNCATED]...\n\n{end_text}"

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