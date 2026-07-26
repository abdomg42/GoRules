# streamlit run streamlit_app.py


import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
HTTP_TIMEOUT = 300  # l'embedding et la generation Ollama peuvent etre longs

NEW_PROJECT = "+ Nouveau projet"

st.set_page_config(page_title="Assistant Projet", layout="wide")


def backend_ok() -> bool:
    try:
        return requests.get(f"{BACKEND_URL}/health", timeout=5).status_code == 200
    except requests.RequestException:
        return False


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
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def ask_question(project_id: str, question: str, top_k: int = 6) -> dict:
    response = requests.post(
        f"{BACKEND_URL}/project/{project_id}/query",
        json={"question": question, "top_k": top_k},
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


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
    st.title("Assistant projet")
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
                st.rerun()

# ---------------- Zone principale : chat ----------------

st.header(f"Assistant documentaire — {project_id}" if project_id else "Assistant documentaire")

if not project_id:
    st.info("Selectionnez un projet existant ou creez-en un dans la barre laterale.")
    st.stop()

history_key = f"history_{project_id}"
st.session_state.setdefault(history_key, [])

for message in st.session_state[history_key]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources", []))

question = st.chat_input("Posez votre question (risques, jalons, avancement...)")
if question:
    st.session_state[history_key].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Recherche dans les documents et generation de la reponse..."):
            try:
                result = ask_question(project_id, question)
            except requests.RequestException as exc:
                answer, sources = error_message(exc), []
            else:
                answer = result.get("answer", "(reponse vide)")
                sources = result.get("sources", [])
        st.markdown(answer)
        render_sources(sources)

    st.session_state[history_key].append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
