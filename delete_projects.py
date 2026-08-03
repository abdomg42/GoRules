"""Supprime des projets (collections Chroma).

Usage : python delete_projects.py demo1 projet1 test12 demo
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

load_dotenv(ROOT_DIR / ".env")

# Meme resolution de CHROMA_DIR que main.py (relatif a src/)
_chroma_dir = Path(os.getenv("CHROMA_DIR", "./chroma_data"))
if not _chroma_dir.is_absolute():
    _chroma_dir = SRC_DIR / _chroma_dir

import chromadb

client = chromadb.PersistentClient(path=str(_chroma_dir))
existing = {getattr(c, "name", str(c)) for c in client.list_collections()}

if len(sys.argv) < 2:
    print("Projets existants :", ", ".join(sorted(existing)) or "(aucun)")
    print("Usage : python delete_projects.py <projet> [<projet> ...]")
    sys.exit(0)

for name in sys.argv[1:]:
    if name in existing:
        client.delete_collection(name)
        print(f"Supprime : {name}")
    else:
        print(f"Inexistant : {name}")
