from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScorerResult:
    score: float       # 0.0 – 1.0
    passed: bool
    label: str         # "pass" | "fail"
    reasoning: str
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "passed": self.passed,
            "label": self.label,
            "reasoning": self.reasoning,
            "raw": self.raw,
        }


class BaseScorer(ABC):
    scorer_type: str = "deterministic"

    def __init__(self, config: dict):
        self.config = config
        self.threshold: float = float(config.get("threshold", 0.5))

    @abstractmethod
    def score(
        self,
        input: str,
        output: str,
        expected: Optional[str] = None,
        context: Optional[str] = None,
        retrieved_chunks: Optional[list[dict]] = None,
    ) -> ScorerResult:
        ...

    def _result(self, score: float, reasoning: str, raw: Optional[dict] = None) -> ScorerResult:
        score = round(max(0.0, min(1.0, score)), 4)
        passed = score >= self.threshold
        return ScorerResult(
            score=score,
            passed=passed,
            label="pass" if passed else "fail",
            reasoning=reasoning,
            raw=raw or {},
        )
