from dataclasses import dataclass

from config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS
from ingestion.parsing import Section

@dataclass
class Chunk:
    chunk_id: str
    document_name: str
    section_label: str
    content: str
    project_id : str

class Chunker:

    def __init__(self, chunk_size_words: int = CHUNK_SIZE_WORDS, chunk_overlap_words: int = CHUNK_OVERLAP_WORDS):
        self.chunk_size_words = chunk_size_words
        self.chunk_overlap_words = chunk_overlap_words

    def chunk_sections(
        self,
        sections: list[Section],
        document_name: str,
        project_id: str | None = None,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        counter = 0
        for section in sections:
            words = section.text.split()
            if not words:
                continue
            start = 0
            while start < len(words):
                end = start + CHUNK_SIZE_WORDS
                piece = " ".join(words[start:end])
                counter += 1
                chunks.append(
                    Chunk(
                        chunk_id=f"{document_name}_{counter}",
                        document_name=document_name,
                        section_label=section.label,
                        content=piece,
                        project_id=project_id,
                    )
                )
                if end >= len(words):
                    break
                start = end - CHUNK_OVERLAP_WORDS
        return chunks

