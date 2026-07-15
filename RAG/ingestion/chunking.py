
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter 
from RAG.ingestion.parser import DocumentParsing

from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: str
    document_name: str
    section_label: str
    content: str

class Chunk_section: 
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size 
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,            
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )
    def chunk_document(self, file_path):
        document_parser = DocumentParsing()
        text = document_parser.parse(file_path=file_path)
        chunks = self.text_splitter.split_text(text)
        chunk_objects = []
        # for section in sections:
        #     for piece in section.text_splitter.split_text(section.content):
        #         chunk.append(Chunk(
        #             chunk_id = str(uuid.uuid4()),
        #             document_id=document_id,
        #             project_id=project_id,
        #             section_label=section.label,
        #             content=piece,
        #         ))
        # return chunk 
        for i, chunk in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            document_name = file_path.split("/")[-1]
            section_label = f"Section {i + 1}"
            chunk_objects.append(Chunk(chunk_id, document_name, section_label, chunk))
        return chunk_objects

