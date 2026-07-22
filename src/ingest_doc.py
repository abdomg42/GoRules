import argparse
from pathlib import Path


from ingestion.parsing import Parser
from ingestion.chunking import Chunker
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

    document_name = file_path.stem
    _parser = Parser(str(file_path))
    _chunker = Chunker()
    print(f"---start parsing {file_path}---")
    sections = _parser.parse_document()
    print(f"--- {len(sections)} sections extraites")

    print("--- Chunking")
    chunks = _chunker.chunk_sections(sections, document_name=str(document_name), project_id=args.project)
    print(f"--->{len(chunks)} chunks generes ")

    print("--- Indexation")
    add_chunks(args.project, chunks)
    print(f"--- {len(chunks)} chunks indexes dans le projet '{args.project}'")


if __name__ == "__main__":
    main()