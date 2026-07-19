import argparse
from pathlib import Path


from ingestion.parsing import parse_document
from ingestion.chunking import chunk_sections
from store import add_chunks


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_input_path(file_arg: str) -> Path:
    candidate = Path(file_arg)
    if candidate.exists():
        return candidate

    root_candidate = PROJECT_ROOT / file_arg
    if root_candidate.exists():
        return root_candidate

    raise FileNotFoundError(
        f"Fichier introuvable: {file_arg}. Essaye un chemin absolu ou relatif au dossier {PROJECT_ROOT}."
    )


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--file",required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()

    file_path = resolve_input_path(args.file)

    document_id = file_path.stem

    print(f"---start parsing {file_path}---")
    sections = parse_document(str(file_path))
    print(f"--- {len(sections)} sections extraites")

    print("--- Chunking")
    
    chunks = chunk_sections(sections, document_name=document_id, project_id=args.project)
    print(f"--->{len(chunks)} chunks generes ")

    print("--- Indexation")
    add_chunks(args.project, chunks)
    print(f"--- {len(chunks)} chunks indexes dans le projet '{args.project}'")


if __name__ == "__main__":
    main()