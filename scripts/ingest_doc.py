import argparse
from pathlib import Path 

from ingestion.parsing import DocumentParsing
from ingestion.chunking import Chunk_section


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--file",required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()

    document_id = Path(args.file).stem

    print(f"---start parsing {args.file}---")
    sections = DocumentParsing().parse(args.file)
    print(f"--- {len(sections)} sections extraites")

    print("--- Chunking")
    
    chunks = Chunk_section().chunk_document(sections,document_id=document_id, project_id=args.project)
    print(f"--->{len(chunks)} chunks generes ")

    print("--- embeddings")
    # à faire 