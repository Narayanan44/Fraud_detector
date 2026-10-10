"""
Risk engine: the "brain" of the project.

It is plain Python (no database, no FastAPI) so it is easy to read and test.
Idea: every rule looks at the new transaction + the customer's past
transactions, and gives some points. Total points = risk score (max 100).
"""
from datetime import timedelta
from statistics import median

# ---------------- Settings: change the numbers here ----------------
HIGH_AMOUNT_LIMIT = 50000      # any single transaction above this is risky
MIN_HISTORY = 3                # need this many past successful transactions to compare

BIG_AMOUNT_RATIO = 5           # amount is 5x the customer's usual amount
MEDIUM_AMOUNT_RATIO = 3

FREQUENCY_WINDOW_MIN = 10      # look at the last 10 minutes
FREQUENCY_HIGH = 5             # 5 or more transactions in the window
FREQUENCY_MEDIUM = 3

SPENDING_RATIO = 3             # last 24h spending is 3x the usual daily spending
MIN_SPEND_TO_CHECK = 1000      # ignore tiny spending, avoids false alarms

FAILED_WINDOW_MIN = 30         # look at the last 30 minutes
FAILED_HIGH = 3
FAILED_MEDIUM = 2

FAST_TRAVEL_MIN = 60           # location changed within 60 minutes

MEDIUM_LEVEL_FROM = 30         # score 30-59 = MEDIUM
HIGH_LEVEL_FROM = 60           # score 60+   = HIGH


def clean_text(text):
    """Make locations comparable: ' Chennai ' and 'chennai' are the same."""
    if not text:
        return ""
    return text.strip().lower()


# ---------------- Rule 1: unusually high amount ----------------
def check_high_amount(txn, history, good_history):
    options = []  # list of (points, message), we keep the biggest one

    if txn["amount"] >= HIGH_AMOUNT_LIMIT:
        options.append((35, f"Amount {txn['amount']} is above the fixed limit of {HIGH_AMOUNT_LIMIT}"))

    if len(good_history) >= MIN_HISTORY:
        usual_amount = median([t["amount"] for t in good_history])  # median ignores old outliers
        if usual_amount > 0:
            ratio = txn["amount"] / usual_amount
            if ratio >= BIG_AMOUNT_RATIO:
                options.append((30, f"Amount is {ratio:.1f}x the customer's usual amount ({usual_amount:.0f})"))
            elif ratio >= MEDIUM_AMOUNT_RATIO:
                options.append((20, f"Amount is {ratio:.1f}x the customer's usual amount ({usual_amount:.0f})"))

    if not options:
        return 0, None
    return max(options)  # tuple compare -> highest points wins


# ---------------- Rule 2: too many transactions in a short time ----------------
def check_frequency(txn, history, good_history):
    start = txn["time"] - timedelta(minutes=FREQUENCY_WINDOW_MIN)
    count = 1  # the new transaction itself
    for t in history:
        if t["time"] >= start:
            count += 1

    message = f"{count} transactions in {FREQUENCY_WINDOW_MIN} minutes"
    if count >= FREQUENCY_HIGH:
        return 25, message
    if count >= FREQUENCY_MEDIUM:
        return 15, message
    return 0, None


# ---------------- Rule 3: sudden change in spending ----------------
def check_spending_change(txn, history, good_history):
    if len(good_history) < MIN_HISTORY:
        return 0, None

    now = txn["time"]
    one_day_ago = now - timedelta(days=1)
    eight_days_ago = now - timedelta(days=8)

    # money spent in the last 24 hours (only successful payments are real spending)
    spent_today = sum(t["amount"] for t in good_history if t["time"] >= one_day_ago)
    if txn["status"] == "success":
        spent_today += txn["amount"]

    # usual daily spending = the 7 days before that (oldest first because history is sorted)
    earlier = [t for t in good_history if eight_days_ago <= t["time"] < one_day_ago]
    if len(earlier) == 0 or spent_today < MIN_SPEND_TO_CHECK:
        return 0, None

    # A new customer may have only 2 days of history, so divide by the days we really have (1 to 7)
    days_covered = (one_day_ago - earlier[0]["time"]).total_seconds() / 86400
    days_covered = min(7, max(1, days_covered))
    usual_daily = sum(t["amount"] for t in earlier) / days_covered

    if usual_daily == 0:
        return 0, None

    ratio = spent_today / usual_daily
    if ratio >= SPENDING_RATIO:
        return 20, f"Spent {spent_today:.0f} in 24 hours, {ratio:.1f}x the usual daily spending ({usual_daily:.0f})"
    return 0, None


# ---------------- Rule 4a: location never used before ----------------
def check_new_location(txn, history, good_history):
    place = clean_text(txn["location"])
    if place == "" or len(good_history) < MIN_HISTORY:
        return 0, None

    known_places = {clean_text(t["location"]) for t in good_history}
    known_places.discard("")          # payments without a location tell us nothing
    if len(known_places) == 0:
        return 0, None                # we never knew any location, so nothing to compare with
    if place not in known_places:
        return 15, f"New location '{txn['location']}', customer never used it before"
    return 0, None


# ---------------- Rule 4b: location changed too fast ----------------
def check_fast_location_change(txn, history, good_history):
    place = clean_text(txn["location"])
    if place == "" or len(history) == 0:
        return 0, None

    last = history[-1]  # history is sorted, so the last item is the most recent
    last_place = clean_text(last["location"])
    minutes = (txn["time"] - last["time"]).total_seconds() / 60

    if last_place != "" and last_place != place and minutes <= FAST_TRAVEL_MIN:
        return 20, f"Location changed from '{last['location']}' to '{txn['location']}' in {minutes:.0f} minutes"
    return 0, None


# ---------------- Rule 5: many failed transactions ----------------
def check_failed_attempts(txn, history, good_history):
    start = txn["time"] - timedelta(minutes=FAILED_WINDOW_MIN)
    failed_count = 0
    for t in history:
        if t["status"] == "failed" and t["time"] >= start:
            failed_count += 1
    if txn["status"] == "failed":
        failed_count += 1

    message = f"{failed_count} failed transactions in {FAILED_WINDOW_MIN} minutes"
    if failed_count >= FAILED_HIGH:
        return 30, message
    if failed_count >= FAILED_MEDIUM:
        return 15, message
    return 0, None


# All rules in one list. To add a new rule: write a function and add it here.
RULES = [
    ("High amount", check_high_amount),
    ("High frequency", check_frequency),
    ("Spending change", check_spending_change),
    ("New location", check_new_location),
    ("Fast location change", check_fast_location_change),
    ("Failed attempts", check_failed_attempts),
]


def get_risk_level(score):
    if score >= HIGH_LEVEL_FROM:
        return "HIGH"
    if score >= MEDIUM_LEVEL_FROM:
        return "MEDIUM"
    return "LOW"


def calculate_risk(txn, user_history):
    """
    txn          : dict with amount, time (datetime), location, status
    user_history : list of dicts (same keys) of this customer's other transactions
    returns      : dict with score (0-100), level, reasons (list)
    """
    # 1. only use transactions that happened before this one, oldest first
    history = [t for t in user_history if t["time"] <= txn["time"]]
    history.sort(key=lambda t: t["time"])

    # 2. "good" history = successful ones. Failed attempts are not normal behaviour.
    good_history = [t for t in history if t["status"] == "success"]

    # 3. run every rule and collect the points
    total = 0
    reasons = []
    for rule_name, rule_function in RULES:
        points, message = rule_function(txn, history, good_history)
        if points > 0:
            total += points
            reasons.append({"rule": rule_name, "points": points, "message": message})

    # 4. extra information, not points
    if len(good_history) < MIN_HISTORY:
        reasons.append({"rule": "Not enough history", "points": 0,
                        "message": "Customer has very little history, so history-based rules were skipped"})
    if not reasons:
        reasons.append({"rule": "Normal", "points": 0, "message": "No suspicious behaviour found"})

    score = min(total, 100)  # cap at 100
    return {"score": score, "level": get_risk_level(score), "reasons": reasons}
