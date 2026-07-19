
from src.agent.embedding import EmbeddingClient


def ask(question: str, retrieved_chunks: list[dict]) -> str:
    if not retrieved_chunks:
        return (
            "Aucun document pertinent trouve dans ce projet pour repondre "
            "a cette question. Avez-vous bien importe des documents "
            "(commande : python ingest.py --project ... --file ...) ?"
        )

    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY manquante. Renseignez-la dans votre fichier .env "
            "(cf. .env.example)."
        )

    context = "\n\n---\n\n".join(
        f"[Source : {c['document_name']}, section \"{c['section_label']}\"]\n{c['content']}"
        for c in retrieved_chunks
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Question : {question}\n\nContexte documentaire disponible :\n{context}",
            }
        ],
    )
    return "".join(block.text for block in response.content if block.type == "text")