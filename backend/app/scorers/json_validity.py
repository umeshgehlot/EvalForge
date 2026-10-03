import json
from typing import Optional
from app.scorers.base import BaseScorer, ScorerResult


class JsonValidityScorer(BaseScorer):
    scorer_type = "deterministic"

    def score(
        self,
        input: str,
        output: str,
        expected: Optional[str] = None,
        context: Optional[str] = None,
        retrieved_chunks: Optional[list[dict]] = None,
    ) -> ScorerResult:
        try:
            parsed = json.loads(output)
            return self._result(
                1.0,
                "Output is valid JSON.",
                {"parsed_type": type(parsed).__name__},
            )
        except json.JSONDecodeError as e:
            return self._result(0.0, f"Invalid JSON: {e}")
