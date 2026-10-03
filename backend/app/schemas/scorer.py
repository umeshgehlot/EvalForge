from typing import Any, Optional
from pydantic import BaseModel


class ScorerCreate(BaseModel):
    name: str
    scorer_type: str  # exact_match | keyword_coverage | json_validity | llm_judge | ragas_faithfulness
    config_json: dict = {}
    prompt_template: Optional[str] = None


class ScorerRead(BaseModel):
    id: int
    name: str
    scorer_type: str
    config_json: Any = {}
    prompt_template: Optional[str] = None

    model_config = {"from_attributes": True}


class ScorerTestRequest(BaseModel):
    input: str
    output: str
    expected: Optional[str] = None
    context: Optional[str] = None
    retrieved_chunks: Optional[list[dict]] = None


class ScorerTestResult(BaseModel):
    score: float
    passed: bool
    label: str
    reasoning: str
    raw: dict = {}
