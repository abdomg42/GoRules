from pathlib import Path

import sys
import urllib.request
import urllib.error

ROOT_DIR = Path(__file__).resolve().parent
print(f"ROOT_DIR={ROOT_DIR}")
SRC_DIR = ROOT_DIR / "src"
print(f"SRC_DIR={SRC_DIR}")

sys.path.insert(0, str(SRC_DIR))
print(f"sys.path={sys.path}")
from prompt import SYSTEM_PROMPT

import urllib 
import json
from config import OLLAMA_BASE_URL , LLM_MODEL
def _ollama_request(path, playload):
    url=f"{OLLAMA_BASE_URL.rstrip('/')}/{path}"
    request = urllib.request.Request(
        url,
        data=json.dumps(playload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try: 
        with urllib.request.urlopen(request, timeout=100) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read()
        raise RuntimeError(f"Erreur Ollama sur {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Impossible de joindre Ollama sur {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Reponse Ollama invalide depuis {url}: {exc}") from exc
def _ask(query, retrieved_chunks):
    if not retrieved_chunks:
        return (
           """ Aucun doc pertinent trouve dans ce projet pour repondre a cette question. avez vouz importer les documents?"""
        )
    context="/n---/n".join(
        f"[Source: {c['document_name']}, section: \"{c['section_label']}\"]\n{c['content']}"
        for c in retrieved_chunks
    )
    playload = {
        "system": SYSTEM_PROMPT,
        "prompt": f"Question: {query}\n\nContexte documentaire disponible:\n{context}",
        "stream": True,
    }
    try: 
        data = {}
        last_exc = None
        model_name = LLM_MODEL
        playload = {**playload, "model": model_name}
        data = _ollama_request('api/generate', playload)
    except Exception as exc:
        except_line = []
        for chunk in retrieved_chunks[:3]:
            snippets = chunk["content"].replace("/n", " ").strip()
            snippets = snippets[:200] + "..." if len(snippets) > 200 else snippets
            except_line.append(f"[Source: {chunk['document_name']}, section: \"{chunk['section_label']}\"]\n{snippets}")
        import socket
        if isinstance(exc, socket.timeout):
            raise RuntimeError(
                f"Timeout lors de l'appel a Ollama. Le modele {model_name} a mis trop de temps a repondre. "
                f"Essayez de reposer la question ou de reduire le nombre de documents pertinents ({len(retrieved_chunks)})."
            ) from exc
    answer = data.get("response","").strip()
    if not answer:
        raise RuntimeError("Ollama n'a returne aucune reponse ")
    return answer
