"""Checks the sample dataset itself, and replays it through the engine."""
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.risk_engine import calculate_risk, get_risk_level

CSV_FILE = Path(__file__).parent.parent / "sample_data" / "transactions.csv"


def read_rows():
    rows = []
    with open(CSV_FILE) as f:
        for line in csv.DictReader(f):
            line["amount"] = float(line["amount"])
            line["time"] = datetime.fromisoformat(line["time"])
            rows.append(line)
    rows.sort(key=lambda r: r["time"])
    return rows


def replay(rows):
    """Score every row using only that user's earlier rows, like the real API does."""
    history_by_user = {}
    results = []
    for row in rows:
        history = history_by_user.setdefault(row["user_id"], [])
        results.append((row, calculate_risk(row, history)))
        history.append(row)
    return results


def test_dataset_is_big_enough():
    rows = read_rows()
    assert len(rows) >= 500
    assert len({r["user_id"] for r in rows}) >= 20


def test_dataset_values_are_valid():
    for row in read_rows():
        assert row["amount"] > 0
        assert row["status"] in ("success", "failed")
        assert row["user_id"].strip() != ""


def test_dataset_has_failed_payments_and_several_cities():
    rows = read_rows()
    assert any(r["status"] == "failed" for r in rows)
    assert len({r["location"] for r in rows}) >= 8


def test_replay_gives_all_three_risk_levels():
    levels = Counter(result["level"] for _, result in replay(read_rows()))
    assert levels["HIGH"] >= 40
    assert levels["MEDIUM"] >= 80
    assert levels["LOW"] >= 300


def test_replay_scores_follow_the_rules():
    for row, result in replay(read_rows()):
        points = sum(r["points"] for r in result["reasons"])
        assert result["score"] == min(points, 100)
        assert result["level"] == get_risk_level(result["score"])
        assert len(result["reasons"]) >= 1


def test_every_rule_fires_somewhere_in_the_dataset():
    fired = set()
    for _, result in replay(read_rows()):
        for reason in result["reasons"]:
            if reason["points"] > 0:
                fired.add(reason["rule"])
    assert fired == {"High amount", "High frequency", "Spending change",
                     "New location", "Fast location change", "Failed attempts"}


def test_many_users_have_a_long_history():
    counts = Counter(r["user_id"] for r in read_rows())
    assert sum(1 for c in counts.values() if c >= 20) >= 20      # repeat customers with rich history


def test_dataset_also_has_new_customers_with_few_payments():
    counts = Counter(r["user_id"] for r in read_rows())
    assert sum(1 for c in counts.values() if c <= 4) >= 3         # new customers
