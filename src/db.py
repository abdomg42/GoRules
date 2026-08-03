"""Persistance PostgreSQL des messages de conversation.

Table `messages` :
- id SERIAL PRIMARY KEY
- project_id TEXT NOT NULL
- role TEXT NOT NULL ("user" / "assistant")
- content TEXT NOT NULL
- sources JSONB
- created_at TIMESTAMP DEFAULT NOW()

L'initialisation est automatique au premier import (appel a init_db()).
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg

from config import DATABASE_URL


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
    sources: list[dict[str, Any]] | None = None
    created_at: datetime | None = None


@contextmanager
def _get_connection():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Cree la table messages si elle n'existe pas."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_project_id
                ON messages (project_id, created_at);
                """
            )
        conn.commit()


def save_message(
    project_id: str,
    role: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
) -> None:
    """Persiste un message dans la base."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (project_id, role, content, sources)
                VALUES (%s, %s, %s, %s);
                """,
                (project_id, role, content, json.dumps(sources) if sources else None),
            )
        conn.commit()


def get_messages(project_id: str, limit: int = 100) -> list[ChatMessage]:
    """Retourne l'historique d'un projet, du plus ancien au plus recent."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content, sources, created_at
                FROM messages
                WHERE project_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT %s;
                """,
                (project_id, limit),
            )
            rows = cur.fetchall()

    messages = []
    for role, content, sources_raw, created_at in rows:
        sources = json.loads(sources_raw) if sources_raw else None
        created_at = created_at.astimezone(timezone.utc) if created_at else None
        messages.append(ChatMessage(role, content, sources, created_at))
    return messages


def delete_messages(project_id: str) -> None:
    """Supprime tous les messages d'un projet."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM messages WHERE project_id = %s;",
                (project_id,),
            )
        conn.commit()



