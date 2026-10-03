from typing import Optional
from app.scorers.base import BaseScorer, ScorerResult


class ExactMatchScorer(BaseScorer):
    scorer_type = "deterministic"

    def score(
        self,
        input: str,
        output: str,
        expected: Optional[str] = None,
        context: Optional[str] = None,
        retrieved_chunks: Optional[list[dict]] = None,
    ) -> ScorerResult:
        if expected is None:
            return self._result(0.0, "No expected output provided.")

        match = output.strip().lower() == expected.strip().lower()
        if match:
            return self._result(1.0, "Output exactly matches expected answer.")
        return self._result(
            0.0,
            f"Mismatch. Expected: '{expected[:120]}' | Got: '{output[:120]}'",
        )
