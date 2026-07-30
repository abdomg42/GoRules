
import json
import socket
import urllib.error
import urllib.request

from config import  LLM_MODEL, OLLAMA_BASE_URL
from prompt import SYSTEM_PROMPT


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


def _build_user_prompt(question: str, retrieved_chunks: list[dict]) -> str:
    if not retrieved_chunks:
        return (
            f"Question : {question}\n\n"
            "Aucun contexte documentaire n'est disponible pour cette question "
            "(aucun document pertinent indexe dans ce projet)."
        )
    context = "\n\n---\n\n".join(
        f"[Source : {c['document_name']}, section \"{c['section_label']}\"]\n{c['content']}"
        for c in retrieved_chunks
    )
    return f"Question : {question}\n\nContexte documentaire disponible :\n{context}"


def ask(question: str, retrieved_chunks: list[dict]) -> str:
    base_payload = {
        "system": SYSTEM_PROMPT,
        "prompt": _build_user_prompt(question, retrieved_chunks),
        "stream": False,
        # Laisser Ollama utiliser le GPU configure nativement (pas de fallback CPU ici).
        "options": {"num_predict": 1200},
    }

    models_to_try = [LLM_MODEL]
    

    try:
        data = {}
        last_exc = None
        for model_name in models_to_try:
            payload = {**base_payload, "model": model_name}
            try:
                data = _ollama_request("/api/generate", payload)
                break
            except Exception as exc:
                last_exc = exc
        else:
            raise last_exc if last_exc else RuntimeError("Aucun modele LLM disponible")
    except Exception as exc:
        excerpt_lines = []
        for chunk in retrieved_chunks[:3]:
            snippet = chunk["content"].replace("\n", " ").strip()
            snippet = snippet[:220] + ("..." if len(snippet) > 220 else "")
            excerpt_lines.append(
                f"- Source: {chunk['document_name']} / {chunk['section_label']}\n  Extrait: {snippet}"
            )

        if isinstance(exc, socket.timeout):
            reason = "timeout de generation"
        else:
            reason = str(exc)

        return (
            "Le contexte documentaire a bien ete retrouve, mais Ollama n'a pas pu generer "
            "la reponse en mode GPU.\n"
            f"Modeles testes: {', '.join(models_to_try)}\n"
            f"Erreur: {reason}\n\n"
            "Conseil: utilisez un modele plus leger cote GPU via la variable "
            f"Question: {question}\n\n"
            "Extraits pertinents:\n"
            + "\n".join(excerpt_lines)
        )

    if "error" in data:
        raise RuntimeError(f"Ollama a retourne une erreur : {data['error']}")

    answer = data.get("response", "").strip()
    if not answer:
        raise RuntimeError("Ollama n'a retourne aucune reponse.")
    return answer


def ask_stream(question: str, retrieved_chunks: list[dict]):
    """Comme ask(), mais stream la reponse token par token (NDJSON Ollama)."""
    payload = {
        "model": LLM_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": _build_user_prompt(question, retrieved_chunks),
        "stream": True,
        "options": {"num_predict": 1200},
    }
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            data = json.loads(line)
            piece = data.get("response", "")
            if piece:
                yield piece
            if data.get("done"):
                break   
    