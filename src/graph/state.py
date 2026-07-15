
from  typing import Optional, TypedDict

class GraphState(TypedDict, totla=False):

    projet_id: str
    question: str
    intent: str
    retrieved_chunks: list[dict]
    extracted_rules: list[dict]
    extracted_requirements: list[dict]
    validation_report: dict
    final_answer: str
    notes: Optional[str]
