"""
Runs every case from engine_cases.py through the risk engine.
Each case is reported as its own test, e.g. test_case[amount_5x_boundary].
"""
import pytest

from app.risk_engine import calculate_risk, get_risk_level
from engine_cases import CASES


def points_that_fired(result):
    return {r["rule"]: r["points"] for r in result["reasons"] if r["points"] > 0}


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_case(case):
    result = calculate_risk(case["txn"], case["history"])

    assert points_that_fired(result) == case["expected"]                   # right rules, right points
    assert result["score"] == min(sum(case["expected"].values()), 100)     # score = total, capped at 100
    assert result["level"] == case["level"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_result_is_always_well_formed(case):
    result = calculate_risk(case["txn"], case["history"])

    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100
    assert result["level"] in ("LOW", "MEDIUM", "HIGH")
    assert len(result["reasons"]) >= 1                                    # always an explanation
    for reason in result["reasons"]:
        assert reason["rule"] and reason["message"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_engine_does_not_change_its_input(case):
    history_before = [dict(t) for t in case["history"]]
    calculate_risk(case["txn"], case["history"])
    assert case["history"] == history_before


@pytest.mark.parametrize("score, level", [
    (0, "LOW"), (29, "LOW"), (30, "MEDIUM"), (59, "MEDIUM"), (60, "HIGH"), (100, "HIGH"),
])
def test_level_boundaries(score, level):
    assert get_risk_level(score) == level