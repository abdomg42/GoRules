from src.config import LLM_MODEL, OLLAMA_BASE_URL

import json
from pathlib import Path
import urllib.error
import urllib.request
from tenacity import retry, stop_after_attempt

PROMPT_DIR = Path(__file__).parent / "prompts"

class LLMBase:
    def __init__(self, llm_model= LLM_MODEL, base_url = OLLAMA_BASE_URL):
        self.llm_model = llm_model
        self.base_url = base_url.rstrip("/")
    def get_model(self):
        return self.llm_model
    def read_prompt(self, prompt_name:str):
        prompt_path = PROMPT_DIR / f'{prompt_name}.txt'       
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding='utf-8')
    @retry(stop_after_attempt(5))
    def _call_llm(self, playload) -> None:
        url = f"{self.base_url}/api/generate"
        request = urllib.request.Request(
            url,
            data=json.dumps(playload).encode("utf-8"),
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
        return None
    # def ask(self, question, retrieved_chunks):
    #     if not retrieved_chunks:
    #         return (
    #             "Aucun document pertinent trouve dans ce projet pour repondre "
    #         )
    #     context = "\n\n---\n\n".join(
    #         f"[Source : {c['document_name']}, section \"{c['section_label']}\"]\n{c['content']}" for c in retrieved_chunks
    #     ) 
    #     playload = {
    #         "model":self.model,
    #         "system": self.read_prompt("system"),
    #         "prompt": f"Question : {question}\n\n Contexte documentaire disponible :\n\n{context}"
    #     }
    #     return playload 
    @staticmethod
    def _parseJson(raw_text:str) :
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
            cleaned = cleaned.split("\n",1)[-1] if cleaned.lower().startswith("json") else cleaned
        try: 
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Erreur de parsing JSON: {exc.msg}. Texte brut: {raw_text}") from exc
    def run(self, question:str, retrieved_chunks:list[dict]) -> dict:
        if not retrieved_chunks:
            return {
                "answer": "Aucun document pertinent trouve dans ce projet pour repondre",
                "sources": []
            }
        context = "\n\n---\n\n".join(
            f"[Source : {c['document_name']}, section \"{c['section_label']}\"]\n{c['content']}" for c in retrieved_chunks
        ) 
        playload = {
            "model":self.llm_model,
            "system": self.read_prompt("system"),
            "prompt": f"Question : {question}\n\n Contexte documentaire disponible :\n\n{context}"
        }
        response = self._call_llm(playload)
        if not response or 'text' not in response:
            raise RuntimeError(f"Reponse invalide de l'IA: {response}")
        return self._parseJson(response['text'])