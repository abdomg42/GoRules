from RAG.ingestion.parser import DocumentParsing 
from RAG.ingestion.chunking import Chunk_section

# parser = DocumentParsing()
# out = parser.parse("test.pdf")
chunker = Chunk_section()
chunks = chunker.chunk_document(file_path="test.pdf")
print(chunks[-1])

