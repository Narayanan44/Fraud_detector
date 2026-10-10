"""
Tests for the risk engine. Run with:  pytest
No database needed because the engine is plain Python.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.risk_engine import calculate_risk

NOW = datetime(2026, 10, 8, 12, 0, 0)


def make_txn(amount=500, minutes_ago=0, location="Chennai", status="success"):
    return {"amount": amount, "time": NOW - timedelta(minutes=minutes_ago),
            "location": location, "status": status}


def normal_history():
    """Customer who spends about 500 in Chennai, once a day, for 5 days."""
    return [make_txn(500, minutes_ago=days * 24 * 60 + 120) for days in range(2, 7)]


def rule_names(result):
    return [r["rule"] for r in result["reasons"] if r["points"] > 0]


def test_normal_transaction_is_low_risk():
    result = calculate_risk(make_txn(520), normal_history())
    assert result["score"] == 0
    assert result["level"] == "LOW"


def test_amount_much_higher_than_usual():
    result = calculate_risk(make_txn(4000), normal_history())   # 8x usual
    assert "High amount" in rule_names(result)


def test_amount_above_fixed_limit_without_history():
    result = calculate_risk(make_txn(80000), [])                # brand new customer
    assert result["score"] == 35
    assert result["level"] == "MEDIUM"
    assert "Not enough history" in [r["rule"] for r in result["reasons"]]


def test_many_transactions_in_short_time():
    history = [make_txn(300, minutes_ago=m) for m in (1, 2, 3, 4)]
    result = calculate_risk(make_txn(300), history)             # 5th in 10 minutes
    assert "High frequency" in rule_names(result)


def test_sudden_spending_increase():
    history = normal_history() + [make_txn(900, minutes_ago=60)]
    result = calculate_risk(make_txn(900), history)             # 1800 today vs ~70 usual
    assert "Spending change" in rule_names(result)


def test_small_spending_is_ignored():
    history = normal_history() + [make_txn(100, minutes_ago=60)]
    result = calculate_risk(make_txn(100), history)             # ratio is high but amount tiny
    assert "Spending change" not in rule_names(result)


def test_new_location():
    result = calculate_risk(make_txn(500, location="Paris"), normal_history())
    assert "New location" in rule_names(result)


def test_location_comparison_ignores_case_and_spaces():
    result = calculate_risk(make_txn(500, location="  CHENNAI "), normal_history())
    assert "New location" not in rule_names(result)


def test_fast_location_change():
    history = normal_history() + [make_txn(500, minutes_ago=20, location="Chennai")]
    result = calculate_risk(make_txn(500, location="Delhi"), history)
    assert "Fast location change" in rule_names(result)


def test_slow_location_change_is_fine():
    history = normal_history() + [make_txn(500, minutes_ago=300, location="Chennai")]
    result = calculate_risk(make_txn(500, location="Delhi"), history)
    assert "Fast location change" not in rule_names(result)


def test_multiple_failed_transactions():
    history = [make_txn(100, minutes_ago=m, status="failed") for m in (2, 4)]
    result = calculate_risk(make_txn(100, status="failed"), history)   # 3rd failure
    assert "Failed attempts" in rule_names(result)


def test_old_failed_transactions_are_ignored():
    history = [make_txn(100, minutes_ago=m, status="failed") for m in (300, 400, 500)]
    result = calculate_risk(make_txn(100), history)
    assert "Failed attempts" not in rule_names(result)


def test_location_seen_only_in_failed_attempt_is_still_new():
    history = normal_history() + [make_txn(100, minutes_ago=2000, location="Paris", status="failed")]
    result = calculate_risk(make_txn(500, location="Paris"), history)
    assert "New location" in rule_names(result)


def test_score_never_goes_above_100():
    history = normal_history() + [make_txn(5000, minutes_ago=m, location="Moscow", status="failed") for m in (1, 2, 3, 4)]
    result = calculate_risk(make_txn(90000, location="Moscow"), history)
    assert result["score"] == 100
    assert result["level"] == "HIGH"


def test_future_transactions_are_ignored():
    future = make_txn(900, minutes_ago=-30)                      # happens after the new one
    result = calculate_risk(make_txn(500), normal_history() + [future])
    assert result["score"] == 0


def test_missing_location_does_not_crash():
    result = calculate_risk(make_txn(500, location=None), normal_history())
    assert result["score"] == 0


def test_every_score_has_a_reason():
    result = calculate_risk(make_txn(500), normal_history())
    assert len(result["reasons"]) >= 1


def test_spending_rule_uses_real_number_of_days():
    # only 3 days of history, 1000 per day. Today 1500 is normal, must NOT be flagged.
    history = [make_txn(1000, minutes_ago=days * 24 * 60) for days in (2, 3, 4)]
    result = calculate_risk(make_txn(1500), history)
    assert "Spending change" not in rule_names(result)
