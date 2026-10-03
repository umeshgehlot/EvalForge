"""Unit tests for all scorer implementations and the scorer registry."""
from unittest.mock import MagicMock, patch

import pytest

from app.scorers.base import ScorerResult
from app.scorers.exact_match import ExactMatchScorer
from app.scorers.json_validity import JsonValidityScorer
from app.scorers.keyword_coverage import KeywordCoverageScorer
from app.scorers.llm_judge import LLMCorrectnessJudge
from app.scorers.ragas_faithfulness import RAGASFaithfulnessScorer
from app.scorers.registry import get_scorer


# ── ExactMatchScorer ──────────────────────────────────────────────────────────

class TestExactMatchScorer:
    def setup_method(self):
        self.scorer = ExactMatchScorer({"threshold": 1.0})

    def test_perfect_match(self):
        r = self.scorer.score("q", "hello world", expected="hello world")
        assert r.passed
        assert r.score == 1.0
        assert r.label == "pass"

    def test_case_insensitive_match(self):
        r = self.scorer.score("q", "Hello World", expected="hello world")
        assert r.passed
        assert r.score == 1.0

    def test_mismatch(self):
        r = self.scorer.score("q", "hello", expected="hello world")
        assert not r.passed
        assert r.score == 0.0
        assert r.label == "fail"

    def test_no_expected_returns_fail(self):
        r = self.scorer.score("q", "hello", expected=None)
        assert not r.passed
        assert r.score == 0.0

    def test_whitespace_trimmed(self):
        r = self.scorer.score("q", "  answer  ", expected="answer")
        assert r.passed


# ── KeywordCoverageScorer ─────────────────────────────────────────────────────

class TestKeywordCoverageScorer:
    def setup_method(self):
        self.scorer = KeywordCoverageScorer({"threshold": 0.7})

    def test_full_coverage(self):
        r = self.scorer.score(
            "q",
            "GPT-3 released 2020 OpenAI transformers",
            expected="GPT-3 released 2020 OpenAI",
        )
        assert r.score == 1.0
        assert r.passed

    def test_partial_coverage_above_threshold(self):
        r = self.scorer.score(
            "q",
            "GPT-3 released 2020",
            expected="GPT-3 released 2020 OpenAI",
        )
        # keywords: gpt, 3, released, 2020, openai (5 total)
        # found: gpt, 3, released, 2020 (4/5 = 0.80) → above 0.70
        assert r.score >= 0.7
        assert r.passed

    def test_low_coverage_fails(self):
        r = self.scorer.score(
            "q",
            "I don't know",
            expected="GPT-3 released 2020 OpenAI transformers attention",
        )
        assert r.score < 0.7
        assert not r.passed

    def test_no_expected_returns_fail(self):
        r = self.scorer.score("q", "some output", expected=None)
        assert not r.passed
        assert r.score == 0.0

    def test_stop_words_excluded(self):
        # "the is a" → all stop words, no meaningful keywords
        r = self.scorer.score("q", "anything", expected="the is a")
        # no meaningful keywords → score=1.0 (vacuously true)
        assert r.score == 1.0

    def test_raw_contains_found_and_missing(self):
        r = self.scorer.score("q", "transformers attention", expected="transformers attention BERT")
        assert "found" in r.raw
        assert "missing" in r.raw
        assert "bert" in r.raw["missing"]


# ── JsonValidityScorer ────────────────────────────────────────────────────────

class TestJsonValidityScorer:
    def setup_method(self):
        self.scorer = JsonValidityScorer({"threshold": 1.0})

    def test_valid_object(self):
        r = self.scorer.score("q", '{"key": "value"}')
        assert r.passed
        assert r.score == 1.0
        assert r.raw["parsed_type"] == "dict"

    def test_valid_array(self):
        r = self.scorer.score("q", '[1, 2, 3]')
        assert r.passed
        assert r.raw["parsed_type"] == "list"

    def test_valid_primitive(self):
        r = self.scorer.score("q", '"hello"')
        assert r.passed

    def test_invalid_json(self):
        r = self.scorer.score("q", "not json {")
        assert not r.passed
        assert r.score == 0.0
        assert "Invalid JSON" in r.reasoning

    def test_empty_string_is_invalid(self):
        r = self.scorer.score("q", "")
        assert not r.passed


# ── LLMCorrectnessJudge ───────────────────────────────────────────────────────

def _mock_llm_response(content: str):
    return MagicMock(choices=[MagicMock(message=MagicMock(content=content))])


class TestLLMCorrectnessJudge:
    def setup_method(self):
        self.scorer = LLMCorrectnessJudge({"model": "gpt-4o-mini", "threshold": 0.6})

    @patch("app.scorers.llm_judge.litellm.completion")
    def test_perfect_score_five(self, mock_llm):
        mock_llm.return_value = _mock_llm_response('{"score": 5, "reasoning": "Perfect answer."}')
        r = self.scorer.score("What is AI?", "Artificial intelligence.", "Artificial intelligence.")
        assert r.score == 1.0   # (5-1)/4 = 1.0
        assert r.passed
        assert r.raw["rating"] == 5

    @patch("app.scorers.llm_judge.litellm.completion")
    def test_mid_score_three(self, mock_llm):
        mock_llm.return_value = _mock_llm_response('{"score": 3, "reasoning": "Partially correct."}')
        r = self.scorer.score("q", "some answer", "expected")
        assert r.score == pytest.approx(0.5)   # (3-1)/4 = 0.5
        assert not r.passed  # 0.5 < threshold 0.6

    @patch("app.scorers.llm_judge.litellm.completion")
    def test_score_clamped_to_valid_range(self, mock_llm):
        # Judge returns out-of-range value — should be clamped to [1,5]
        mock_llm.return_value = _mock_llm_response('{"score": 99, "reasoning": "edge case"}')
        r = self.scorer.score("q", "a", "b")
        assert r.score == 1.0  # clamped to 5 → (5-1)/4 = 1.0

    @patch("app.scorers.llm_judge.litellm.completion")
    def test_llm_failure_returns_zero(self, mock_llm):
        mock_llm.side_effect = Exception("Network error")
        r = self.scorer.score("q", "a", "b")
        assert r.score == 0.0
        assert not r.passed
        assert "Judge call failed" in r.reasoning


# ── RAGASFaithfulnessScorer ───────────────────────────────────────────────────

class TestRAGASFaithfulnessScorer:
    def setup_method(self):
        self.scorer = RAGASFaithfulnessScorer({"model": "gpt-4o-mini", "threshold": 0.7})

    @patch("app.scorers.ragas_faithfulness.litellm.completion")
    def test_all_claims_supported(self, mock_llm):
        mock_llm.side_effect = [
            _mock_llm_response('{"claims": ["The sky is blue.", "Water is wet."]}'),
            _mock_llm_response('{"supported": true, "reasoning": "Context supports this."}'),
            _mock_llm_response('{"supported": true, "reasoning": "Context supports this."}'),
        ]
        r = self.scorer.score(
            "q", "The sky is blue and water is wet.",
            context="The sky appears blue due to light scattering. Water is a liquid at room temperature.",
        )
        assert r.score == 1.0
        assert r.passed

    @patch("app.scorers.ragas_faithfulness.litellm.completion")
    def test_no_claims_scores_full(self, mock_llm):
        mock_llm.return_value = _mock_llm_response('{"claims": []}')
        r = self.scorer.score("q", "I don't know.", context="Some context here.")
        assert r.score == 1.0  # vacuously faithful

    def test_no_context_returns_fail(self):
        r = self.scorer.score("q", "answer", context=None, retrieved_chunks=None)
        assert r.score == 0.0
        assert not r.passed
        assert "No context" in r.reasoning

    @patch("app.scorers.ragas_faithfulness.litellm.completion")
    def test_partial_support(self, mock_llm):
        mock_llm.side_effect = [
            _mock_llm_response('{"claims": ["Claim A.", "Claim B."]}'),
            _mock_llm_response('{"supported": true, "reasoning": "ok"}'),
            _mock_llm_response('{"supported": false, "reasoning": "not supported"}'),
        ]
        r = self.scorer.score("q", "answer", context="context")
        assert r.score == pytest.approx(0.5)
        assert not r.passed  # 0.5 < threshold 0.7


# ── Scorer Registry ───────────────────────────────────────────────────────────

class TestScorerRegistry:
    def test_get_known_scorer(self):
        scorer = get_scorer("exact_match", {"threshold": 1.0})
        assert isinstance(scorer, ExactMatchScorer)

    def test_get_all_types(self):
        for scorer_type in ["exact_match", "keyword_coverage", "json_validity"]:
            scorer = get_scorer(scorer_type, {"threshold": 0.5})
            assert scorer is not None

    def test_unknown_scorer_raises(self):
        with pytest.raises(ValueError, match="Unknown scorer type"):
            get_scorer("nonexistent_scorer", {})

    def test_config_passed_to_scorer(self):
        scorer = get_scorer("keyword_coverage", {"threshold": 0.9})
        assert scorer.threshold == 0.9
