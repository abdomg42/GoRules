
import json
import urllib.error
import urllib.request

from config import LLM_MODEL, OLLAMA_BASE_URL


def _ollama_request(path: str, payload: dict) -> dict:
    url = f"{OLLAMA_BASE_URL.rstrip('/')}{path}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Erreur Ollama sur {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Impossible de joindre Ollama sur {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Reponse Ollama invalide depuis {url}: {exc}") from exc


def ask(question: str, retrieved_chunks: list[dict]) -> str:
    if not retrieved_chunks:
        return (
            "Aucun document pertinent trouve dans ce projet pour repondre "
            "a cette question. Avez-vous bien importe des documents "
            "(commande : python ingest.py --project ... --file ...) ?"
        )

    context = "\n\n---\n\n".join(
        f"[Source : {c['document_name']}, section \"{c['section_label']}\"]\n{c['content']}"
        for c in retrieved_chunks
    )

    payload = {
        "model": LLM_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": f"Question : {question}\n\nContexte documentaire disponible :\n{context}",
        "stream": False,
        "options": {"num_predict": 1500},
    }
    data = _ollama_request("/api/generate", payload)

    if "error" in data:
        raise RuntimeError(f"Ollama a retourne une erreur : {data['error']}")

    answer = data.get("response", "").strip()
    if not answer:
        raise RuntimeError("Ollama n'a retourne aucune reponse.")
    return answer