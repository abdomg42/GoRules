from src.config import LLM_MODEL, OLLAMA_BASE_URL

import json
from pathlib import Path


PROMPT_DIR = Path(__file__).parent / "prompts"
class LLMBase:
    def __init__(self, llm_model= LLM_MODEL, base_url = OLLAMA_BASE_URL):
        self.llm_model = llm_model
        self.base_url = base_url.rstrip("/")
    def get_model(self):
        return self.llm_model
    def read_prompt(self, prompt_name:str):
        prompt_path = PROMPT_DIR / f'{prompt_name}.txt'
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    