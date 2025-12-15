import pytesseract
from PIL import Image
import os

def extract_text_from_image(image_path: str) -> str:
    """
    Extracts text from an image file using Tesseract OCR.
    """
    try:
        if not os.path.exists(image_path):
            return ""
        
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"OCR Error on {image_path}: {e}")
        return ""
