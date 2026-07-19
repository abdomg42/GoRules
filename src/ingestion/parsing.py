
from dataclasses import dataclass

from pypdf import PdfReader
from pathlib import Path
from docx import Document as DocxDocument


@dataclass
class Section:
    label: str      
    text: str
    
def parse_document(file_path: str) -> list[Section]:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(file_path)
    if suffix == ".docx":
        return _parse_docx(file_path)
    raise ValueError(f"Format non supporte dans ce MVP : {suffix}")


def _parse_pdf(file_path: str) -> list[Section]:
    reader = PdfReader(file_path)
    sections = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            sections.append(Section(label=f"page_{i}", text=text))
    return sections

def _parse_docx(file_path: str) -> list[Section]:
    doc = DocxDocument(file_path)
    sections: list[Section] = []
    current_label = "introduction"
    buffer: list[str] = []

    def flush():
        if buffer:
            sections.append(Section(label=current_label, text="\n".join(buffer)))
            buffer.clear()

    for para in doc.paragraphs:
        if para.style.name.startswith("Heading") and para.text.strip():
            flush()
            current_label = para.text.strip()
        elif para.text.strip():
            buffer.append(para.text)
    flush()
    return sections
