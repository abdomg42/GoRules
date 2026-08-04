

import fitz 
from PIL import Image
import pytesseract
import io 
from base import LLMBase

class OcrAgent(LLMBase): 
    def __init__(self,pages):
        self.pages = pages
    def pages_needs_ocr(self,page):
        text = page.get_text().strip()
        has_image = len(page.get_images(full=True)) > 0
        return len(text) < 20 and has_image
        

