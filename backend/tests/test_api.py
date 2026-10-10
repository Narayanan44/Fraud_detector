"""
API tests. They use their own SQLite file (test_api.db), so your real database is never touched.
Every test starts with an empty table.
"""
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"   # must be set BEFORE importing the app
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CSV_FILE = Path(__file__).parent.parent / "sample_data" / "transactions.csv"


def setup_function():
    client.delete("/transactions")   # empty table before every test


def add(user="A1", amount=500, time=None, location="Chennai", status="success"):
    body = {"user_id": user, "amount": amount, "location": location, "status": status}
    if time:
        body["time"] = time
    return client.post("/transactions", json=body)


def rules_that_fired(response):
    return [r["rule"] for r in response.json()["reasons"] if r["points"] > 0]


def reason_names(response):
    return [r["rule"] for r in response.json()["reasons"]]


# ---------------- basic ----------------
def test_home_page_works():
    assert client.get("/").status_code == 200


def test_response_has_all_fields():
    data = add(amount=80000, location="Mumbai").json()
    for key in ("id", "user_id", "amount", "location", "status", "time", "risk_score", "risk_level", "reasons"):
        assert key in data
    for reason in data["reasons"]:
        assert set(reason) == {"rule", "points", "message"}


def test_new_customer_huge_payment():
    data = add(amount=80000, location="Mumbai").json()
    assert data["risk_score"] == 35
    assert data["risk_level"] == "MEDIUM"


# ---------------- bad input must be rejected (422) ----------------
@pytest.mark.parametrize("payload", [
    {"user_id": "A1", "amount": 0},
    {"user_id": "A1", "amount": -50},
    {"user_id": "A1"},                                 # amount missing
    {"user_id": "A1", "amount": None},
    {"user_id": "A1", "amount": "abc"},
    {"user_id": "A1", "amount": "inf"},
    {"amount": 100},                                   # user missing
    {"user_id": "", "amount": 100},
    {"user_id": "   ", "amount": 100},                 # only spaces
    {"user_id": "A1", "amount": 100, "status": "maybe"},
    {"user_id": "A1", "amount": 100, "time": "yesterday"},
    {},
])
def test_bad_input_is_rejected(payload):
    assert client.post("/transactions", json=payload).status_code == 422


# ---------------- unusual but valid input must work ----------------
def test_only_required_fields():
    data = client.post("/transactions", json={"user_id": "A1", "amount": 100}).json()
    assert data["status"] == "success"
    assert data["location"] is None


def test_empty_location_is_allowed():
    assert add(location="").status_code == 200


def test_unicode_location():
    data = add(location="சென்னை").json()
    assert data["location"] == "சென்னை"


def test_user_id_spaces_are_trimmed():
    assert add(user="  U1  ").json()["user_id"] == "U1"


def test_tiny_amount():
    data = add(amount=0.01).json()
    assert data["risk_score"] == 0


def test_huge_amount():
    data = add(amount=1e12).json()
    assert data["risk_score"] == 35


def test_time_with_timezone_is_stored_as_given():
    data = add(time="2026-10-08T10:00:00+05:30").json()
    assert data["time"] == "2026-10-08T10:00:00"


def test_missing_time_uses_current_time():
    assert add().json()["time"] is not None


# ---------------- history is remembered between requests ----------------
def test_history_is_used_for_the_next_payment():
    for day in ("01", "02", "03"):
        add(amount=500, time=f"2026-10-{day}T10:00:00")
    response = add(amount=5000, time="2026-10-04T12:00:00")     # 10x the usual
    assert "High amount" in rules_that_fired(response)
    assert response.json()["risk_level"] == "MEDIUM"


def test_users_do_not_affect_each_other():
    for day in range(1, 6):
        add(user="A", amount=500, time=f"2026-10-0{day}T10:00:00")
    response = add(user="B", amount=500, time="2026-10-06T10:00:00")
    assert "Not enough history" in reason_names(response)
    assert response.json()["risk_score"] == 0


def test_payments_older_than_30_days_are_ignored():
    for day in range(1, 6):
        add(amount=500, time=f"2026-08-0{day}T10:00:00")
    response = add(amount=5000, time="2026-10-08T10:00:00")
    assert "Not enough history" in reason_names(response)
    assert response.json()["risk_score"] == 0


def test_backdated_payment_ignores_the_future():
    add(user="A", amount=80000, time="2026-10-10T12:00:00")                 # later payment saved first
    response = add(user="A", amount=100, time="2026-10-01T12:00:00")        # older payment arrives late
    assert response.json()["risk_score"] == 0


def test_failed_payments_in_a_row_are_scored_one_by_one():
    scores = []
    for minute in (0, 2, 4):
        scores.append(add(amount=100, status="failed", time=f"2026-10-08T16:0{minute}:00").json()["risk_score"])
    assert scores[0] == 0       # 1st failure: normal
    assert scores[1] == 15      # 2nd failure: +15
    assert scores[2] == 45      # 3rd failure: +30 failed attempts, +15 because 3 payments in 4 minutes


# ---------------- list, filter, delete ----------------
def test_list_is_newest_first():
    add(user="A", time="2026-10-01T10:00:00")
    add(user="B", time="2026-10-02T10:00:00")
    times = [t["time"] for t in client.get("/transactions").json()]
    assert times == sorted(times, reverse=True)


def test_filter_by_risk_level():
    add(user="A1", amount=80000)
    add(user="A2", amount=100)
    assert len(client.get("/transactions?level=medium").json()) == 1      # lower case works
    assert len(client.get("/transactions?level=LOW").json()) == 1
    assert client.get("/transactions?level=HIGH").json() == []
    assert client.get("/transactions?level=banana").json() == []


def test_delete_all():
    add()
    add()
    assert client.delete("/transactions").json()["deleted"] == 2
    assert client.get("/transactions").json() == []


# ---------------- sample dataset through the real API ----------------
def test_load_sample_data():
    expected_rows = len(CSV_FILE.read_text().strip().splitlines()) - 1     # minus header line
    assert client.post("/load-sample").json()["loaded"] == expected_rows

    items = client.get("/transactions").json()
    assert len(items) == expected_rows
    for item in items:
        assert 0 <= item["risk_score"] <= 100
        assert len(item["reasons"]) >= 1
    assert {i["risk_level"] for i in items} == {"LOW", "MEDIUM", "HIGH"}
