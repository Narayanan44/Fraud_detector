"""
Creates TEST_CASES.md from engine_cases.py so the document always matches the tests.
Run from the backend folder:  python tests/make_test_cases_doc.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from engine_cases import CASES

GROUPS = [
    ("amount", "1. High amount"),
    ("freq", "2. High frequency"),
    ("spend", "3. Sudden spending change"),
    ("loc", "4a. Unusual location (new city)"),
    ("fast", "4b. Location changed too fast"),
    ("failed", "5. Multiple failed transactions"),
    ("combo", "6. Combined patterns"),
    ("data", "7. Data and ordering edge cases"),
]

API_CASES = [
    ("amount = 0", "422 rejected"),
    ("amount = -50", "422 rejected"),
    ("amount missing / null / \"abc\" / \"inf\"", "422 rejected"),
    ("user_id missing, empty, or only spaces", "422 rejected"),
    ("status = \"maybe\"", "422 rejected"),
    ("time = \"yesterday\"", "422 rejected"),
    ("empty body {}", "422 rejected"),
    ("only user_id + amount", "200, status defaults to success, location null"),
    ("location empty or unicode (சென்னை)", "200, saved as given"),
    ("user_id \"  U1  \"", "200, saved as \"U1\""),
    ("amount 0.01 / amount 1e12", "200, scores 0 / 35"),
    ("time with timezone +05:30", "200, stored without converting"),
    ("time missing", "200, current time used"),
    ("3 normal payments, then 10x amount", "High amount fires (history remembered)"),
    ("two users", "history is not shared between users"),
    ("payments older than 30 days", "ignored, 'Not enough history'"),
    ("old payment arrives after a newer one", "scored without looking at the future"),
    ("3 failed payments in 4 minutes", "scores 0, 15, 45"),
    ("filter level=medium / LOW / HIGH / banana", "case-insensitive, unknown level gives empty list"),
    ("DELETE all", "table empty"),
    ("load sample data", "every row saved, scores 0-100, all three levels present"),
]

lines = ["# Test cases", "",
         f"- **Engine scenarios:** {len(CASES)} (each one is checked 3 ways: expected rules and points, valid output, input not modified)",
         "- **Level boundaries:** 0, 29, 30, 59, 60, 100",
         "- **Sample dataset checks:** size, valid values, all levels appear, every rule fires",
         "- **API checks:** see the last table", "",
         "Run all tests: `pytest` (from the `backend` folder). Run one case: `pytest -k amount_5x_boundary`", ""]

for prefix, title in GROUPS:
    lines += [f"## {title}", "", "| Case | What it proves | Expected points | Level |", "|---|---|---|---|"]
    for c in CASES:
        if c["name"].split("_")[0] == prefix:
            total = min(sum(c["expected"].values()), 100)
            if c["expected"]:
                points = ", ".join(f"{rule} +{p}" for rule, p in c["expected"].items()) + f" (score {total})"
            else:
                points = "nothing fires (score 0)"
            lines.append(f"| `{c['name']}` | {c['why']} | {points} | {c['level']} |")
    lines.append("")

lines += ["## API cases", "", "| Request | Expected |", "|---|---|"]
lines += [f"| {a} | {b} |" for a, b in API_CASES]

Path(__file__).parent.parent.joinpath("TEST_CASES.md").write_text("\n".join(lines) + "\n")
print("TEST_CASES.md written with", len(CASES), "engine cases")
