"""Frontend Streamlit de l'assistant documentaire.

Consomme l'API FastAPI definie dans main.py.
Lancement : streamlit run streamlit_app.py
"""

import json
import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
# HTTP_TIMEOUT = 300  # l'embedding et la generation Ollama peuvent etre longs

NEW_PROJECT = "+ New project"

st.set_page_config(page_title="Go Rules ", layout="wide")


# Les appels reseau de la sidebar sont caches : sans ca, chaque interaction
# Streamlit relancerait des requetes HTTP vers le backend a chaque rerun.
@st.cache_data(ttl=10, show_spinner=False)
def backend_ok() -> bool:
    try:
        return requests.get(f"{BACKEND_URL}/health", timeout=5).status_code == 200
    except requests.RequestException:
        return False


@st.cache_data(ttl=5, show_spinner=False)
def fetch_projects() -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/projects", timeout=10)
        response.raise_for_status()
        return response.json().get("projects", [])
    except requests.RequestException:
        return []


def upload_document(project_id: str, filename: str, data: bytes) -> dict:
    response = requests.post(
        f"{BACKEND_URL}/project/{project_id}/documents",
        params={"filename": filename},
        data=data,
        headers={"Content-Type": "application/octet-stream"},
    )
    response.raise_for_status()
    return response.json()


def stream_answer(project_id: str, question: str, top_k: int = 6):
    """Itere les evenements NDJSON du backend (sources, tokens, erreur)."""
    with requests.post(
        f"{BACKEND_URL}/project/{project_id}/query/stream",
        json={"question": question, "top_k": top_k},
        stream=True,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if line:
                yield json.loads(line)


def error_message(exc: requests.RequestException) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return f"Erreur backend ({exc.response.status_code}) : {exc.response.text}"
    return f"Backend injoignable ({BACKEND_URL}). Verifiez qu'uvicorn tourne. Detail : {exc}"


def render_sources(sources: list[dict]) -> None:
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for source in sources:
                st.markdown(
                    f"- `{source['document_name']}` — section *{source['section_label']}*"
                )


# ---------------- Barre laterale : projet + documents ----------------

projects = fetch_projects()
project_names = [p["name"] for p in projects]

with st.sidebar:
    st.title("Go Rules")
    st.caption(f"Backend : {'OK' if backend_ok() else 'injoignable'} — {BACKEND_URL}")

    choice = st.selectbox("Projet", project_names + [NEW_PROJECT])
    if choice == NEW_PROJECT:
        project_id = st.text_input(
            "Nom du nouveau projet",
            placeholder="ex. refonte_si",
            help="Lettres, chiffres, tirets et underscores (contrainte Chroma).",
        ).strip()
    else:
        project_id = choice
        chunks = next((p["chunks"] for p in projects if p["name"] == choice), 0)
        st.caption(f"{chunks} chunks indexes")

    st.divider()
    st.subheader("Importer un document")
    uploaded = st.file_uploader("PDF ou DOCX", type=["pdf", "docx"])
    if st.button("Indexer le document", disabled=not (uploaded and project_id)):
        with st.spinner("Parsing, chunking et indexation en cours..."):
            try:
                result = upload_document(project_id, uploaded.name, uploaded.getvalue())
            except requests.RequestException as exc:
                st.error(error_message(exc))
            else:
                st.success(f"{result['filename']} : {result['chunks']} chunks indexes.")
                fetch_projects.clear()
                st.rerun()

# ---------------- Zone principale : chat ----------------

st.header(f"Your AI Assistant for Business Rules— {project_id}" if project_id else "Assistant documentaire")

if not project_id:
    st.info("Selectionnez un projet existant ou creez-en un dans la barre laterale.")
    st.stop()

history_key = f"history_{project_id}"
st.session_state.setdefault(history_key, [])

for message in st.session_state[history_key]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources", []))

question = st.chat_input("Posez votre question")
if question:
    st.session_state[history_key].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.caption("_Recherche dans les documents…_")
        stream_result: dict = {"sources": [], "error": None, "started": False}

        def token_stream():
            try:
                for event in stream_answer(project_id, question):
                    event_type = event.get("type")
                    if event_type == "sources":
                        stream_result["sources"] = event.get("sources", [])
                    elif event_type == "token":
                        if not stream_result["started"]:
                            stream_result["started"] = True
                            thinking.empty()
                        yield event.get("text", "")
                    elif event_type == "error":
                        stream_result["error"] = event.get("detail", "erreur inconnue")
            except requests.RequestException as exc:
                stream_result["error"] = error_message(exc)

        # Affiche la reponse au fil de sa generation (pas d'attente du texte complet)
        answer = st.write_stream(token_stream())
        thinking.empty()
        sources = stream_result["sources"]
        error = stream_result["error"]
        if error:
            st.error(error)
            answer = f"{answer}\n\n{error}" if answer else error
        render_sources(sources)

    st.session_state[history_key].append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
