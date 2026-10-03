from app.scorers.base import BaseScorer
from app.scorers.exact_match import ExactMatchScorer
from app.scorers.keyword_coverage import KeywordCoverageScorer
from app.scorers.json_validity import JsonValidityScorer
from app.scorers.llm_judge import LLMCorrectnessJudge
from app.scorers.ragas_faithfulness import RAGASFaithfulnessScorer

SCORER_REGISTRY: dict[str, type[BaseScorer]] = {
    "exact_match": ExactMatchScorer,
    "keyword_coverage": KeywordCoverageScorer,
    "json_validity": JsonValidityScorer,
    "llm_judge": LLMCorrectnessJudge,
    "ragas_faithfulness": RAGASFaithfulnessScorer,
}

SCORER_LABELS: dict[str, str] = {
    "exact_match": "Exact Match",
    "keyword_coverage": "Keyword Coverage",
    "json_validity": "JSON Validity",
    "llm_judge": "LLM Correctness Judge",
    "ragas_faithfulness": "RAGAS Faithfulness",
}


def get_scorer(scorer_type: str, config: dict) -> BaseScorer:
    cls = SCORER_REGISTRY.get(scorer_type)
    if cls is None:
        raise ValueError(
            f"Unknown scorer type '{scorer_type}'. "
            f"Available: {list(SCORER_REGISTRY.keys())}"
        )
    return cls(config)
