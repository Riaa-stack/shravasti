import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import io
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize EasyOCR reader (lazily or at startup depending on memory limits)
# We use lazy initialization to save memory if OCR isn't needed
_reader = None

def get_reader():
    logger.warning("EasyOCR is disabled. Scanned images will not be parsed.")
    return None

def extract_text_from_pdf(file_path: str) -> list[dict]:
    """
    Extracts text from a PDF file using PyMuPDF.
    If a page has very low text density (likely a scanned image), falls back to EasyOCR.
    Returns a list of dictionaries with page number and text.
    """
    extracted_pages = []
    
    try:
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            # Simple heuristic: if extracted text length is too small, it might be a scanned image
            # Also check if it's mostly whitespace
            if len(text.strip()) < 50:
                logger.info(f"Page {page_num + 1} has low text density, falling back to OCR.")
                text = _extract_text_ocr(page)
                
            extracted_pages.append({
                "page_number": page_num + 1,
                "text": text.strip()
            })
            
        doc.close()
        return extracted_pages
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        raise

def _extract_text_ocr(page: fitz.Page) -> str:
    """Uses EasyOCR to extract text from a PyMuPDF page rendered as an image."""
    try:
        # Render page to image
        pix = page.get_pixmap(dpi=300) # type: ignore
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_np = np.array(img)
        
        reader = get_reader()
        result = reader.readtext(img_np, detail=0)
        
        return " ".join(result)
    except Exception as e:
        logger.error(f"OCR failed for page: {e}")
        return ""
