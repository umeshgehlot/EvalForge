import re
from typing import Optional
from app.scorers.base import BaseScorer, ScorerResult

_STOP = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for", "of",
    "and", "or", "but", "not", "with", "this", "that", "are", "was",
    "be", "by", "as", "from", "its", "which", "have", "has", "been",
    "will", "can", "do", "does", "did",
}


class KeywordCoverageScorer(BaseScorer):
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
            return self._result(0.0, "No expected output to extract keywords from.")

        keywords = set(re.findall(r"\b\w+\b", expected.lower())) - _STOP
        if not keywords:
            return self._result(1.0, "No meaningful keywords found in expected output.")

        output_lower = output.lower()
        found = {w for w in keywords if w in output_lower}
        missing = keywords - found
        score = len(found) / len(keywords)

        reasoning = (
            f"{len(found)}/{len(keywords)} keywords present ({score:.0%})."
            + (f" Missing: {', '.join(sorted(missing)[:8])}" if missing else "")
        )
        return self._result(
            score,
            reasoning,
            {"found": sorted(found), "missing": sorted(missing)},
        )
