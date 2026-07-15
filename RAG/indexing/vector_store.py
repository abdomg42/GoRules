
from pypdf import PdfReader
from pathlib import Path

class DocumentParsing:
    """for now only pdf files , next step is to add docs and other formats"""
    def parse(self, file_path):
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(file_path)
    
    def _parse_pdf(self, file_path):
        reader = PdfReader(file_path)
        text=""
        for page in reader.pages:
            text += page.extract_text()
        return text


