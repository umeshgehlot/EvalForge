"""Unit tests for the seed.py helper functions (no DB required)."""
import sys
from pathlib import Path

import pytest

# seed.py is at backend/ root, not inside a package
sys.path.insert(0, str(Path(__file__).parent.parent))
from seed import _pf, _p95, _kw_reasoning, _llm_reasoning


class TestPassFail:
    def test_both_above_threshold(self):
        assert _pf(0.75, 0.65) is True

    def test_kw_exactly_at_threshold(self):
        assert _pf(0.70, 0.60) is True

    def test_kw_below_threshold(self):
        assert _pf(0.69, 0.80) is False

    def test_llm_below_threshold(self):
        assert _pf(0.80, 0.59) is False

    def test_both_zero(self):
        assert _pf(0.0, 0.0) is False

    def test_both_one(self):
        assert _pf(1.0, 1.0) is True


class TestP95:
    def test_single_value(self):
        assert _p95([500.0]) == 500.0

    def test_all_same(self):
        assert _p95([100.0] * 10) == pytest.approx(100.0)

    def test_sorted_values(self):
        # [1,2,3,4,5,6,7,8,9,10] p95 = 9.55 (numpy interpolation)
        result = _p95([float(i) for i in range(1, 11)])
        assert result == pytest.approx(9.55, abs=0.1)

    def test_empty_list(self):
        assert _p95([]) == 0.0

    def test_two_values(self):
        # [100, 200] p95: i = 0.95 * 1 = 0.95, lo=0, hi=1
        # result = 100 + 0.95 * (200-100) = 100 + 95 = 195
        assert _p95([100.0, 200.0]) == pytest.approx(195.0)


class TestReasoning:
    def test_kw_pass_message(self):
        msg = _kw_reasoning(0.85)
        assert "85%" in msg
        assert "coverage" in msg.lower()

    def test_kw_fail_message(self):
        msg = _kw_reasoning(0.45)
        assert "45%" in msg
        assert "missing" in msg.lower() or "insufficient" in msg.lower()

    def test_llm_pass_message(self):
        msg = _llm_reasoning(0.75)
        assert "correct" in msg.lower() or "0.75" in msg

    def test_llm_fail_message(self):
        msg = _llm_reasoning(0.30)
        assert "incomplete" in msg.lower() or "inaccur" in msg.lower() or "0.30" in msg
