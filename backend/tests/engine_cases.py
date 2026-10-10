"""
TEST DATA for the risk engine. One entry in CASES = one scenario.

Each case has:
  name     : short id
  why      : what this case proves (also used in TEST_CASES.md)
  history  : the customer's old transactions
  txn      : the new transaction being checked
  expected : {rule name: points} that MUST fire (nothing else may fire)
  level    : LOW / MEDIUM / HIGH

The expected values were worked out by hand from the rules, NOT copied from the program.
"""
from datetime import datetime, timedelta

NOW = datetime(2026, 10, 8, 12, 0, 0)
DAY = 24 * 60  # minutes in a day


def tx(amount, minutes_ago=0, location="Chennai", status="success"):
    """One transaction. minutes_ago=0 means 'right now'. Negative = in the future."""
    return {"amount": amount, "time": NOW - timedelta(minutes=minutes_ago),
            "location": location, "status": status}


def baseline(amount):
    """5 normal successful payments in Chennai, 2 to 6 days ago."""
    return [tx(amount, minutes_ago=d * DAY + 120) for d in range(2, 7)]


# a customer who already uses two cities (Chennai and Delhi)
TWO_CITIES = baseline(100) + [tx(100, minutes_ago=3 * DAY + 30, location="Delhi")]

CASES = []


def add(name, why, history, txn, expected, level):
    CASES.append({"name": name, "why": why, "history": history, "txn": txn,
                  "expected": expected, "level": level})


# =================== 1. HIGH AMOUNT ===================
add("amount_normal", "Normal payment, nothing fires",
    baseline(500), tx(520), {}, "LOW")
add("amount_2_9x_below_rule", "2.9x the usual amount is below the 3x rule",
    baseline(100), tx(290), {}, "LOW")
add("amount_3x_boundary", "Exactly 3x the usual amount -> +20",
    baseline(100), tx(300), {"High amount": 20}, "LOW")
add("amount_4_9x", "4.9x is still the 3x level -> +20",
    baseline(100), tx(490), {"High amount": 20}, "LOW")
add("amount_5x_boundary", "Exactly 5x -> +30 (score 30 is the MEDIUM boundary)",
    baseline(100), tx(500), {"High amount": 30}, "MEDIUM")
add("amount_100x_also_spending", "100x the usual: amount +30 and daily spending +20",
    baseline(500), tx(49999), {"High amount": 30, "Spending change": 20}, "MEDIUM")
add("amount_exactly_fixed_limit_new_customer", "No history, exactly 50000 -> fixed limit +35",
    [], tx(50000), {"High amount": 35}, "MEDIUM")
add("amount_fixed_and_ratio_not_added", "Fixed limit (35) and ratio (30) both apply, only the bigger counts",
    baseline(500), tx(60000), {"High amount": 35, "Spending change": 20}, "MEDIUM")
add("amount_new_customer_small", "New customer, small payment, nothing fires",
    [], tx(500), {}, "LOW")
add("amount_only_two_past_payments", "2 past payments are too few to compare, 5000 is under the fixed limit",
    [tx(500, 2 * DAY), tx(500, 3 * DAY)], tx(5000), {}, "LOW")
add("amount_failed_history_is_no_baseline", "Failed payments are not normal behaviour, so no baseline exists",
    [tx(100, d * DAY, status="failed") for d in range(2, 7)], tx(3000), {}, "LOW")
add("amount_history_of_zero_does_not_crash", "Median of 0 must not cause a divide by zero",
    baseline(0), tx(500), {}, "LOW")
add("amount_huge_new_customer", "Huge number (1e12) works and only fixed limit fires",
    [], tx(1e12), {"High amount": 35}, "MEDIUM")

# =================== 2. HIGH FREQUENCY ===================
add("freq_2_in_10_min", "2 payments in 10 minutes is normal",
    baseline(100) + [tx(100, 3)], tx(100), {}, "LOW")
add("freq_3_in_10_min", "3 payments in 10 minutes -> +15",
    baseline(100) + [tx(100, 2), tx(100, 4)], tx(100), {"High frequency": 15}, "LOW")
add("freq_4_in_10_min", "4 payments still the +15 level",
    baseline(100) + [tx(100, 1), tx(100, 2), tx(100, 3)], tx(100), {"High frequency": 15}, "LOW")
add("freq_5_in_10_min", "5 payments -> +25",
    baseline(100) + [tx(100, m) for m in (1, 2, 3, 4)], tx(100), {"High frequency": 25}, "LOW")
add("freq_6_in_10_min", "6 payments is still +25 (no extra points)",
    baseline(100) + [tx(100, m) for m in (1, 2, 3, 4, 5)], tx(100), {"High frequency": 25}, "LOW")
add("freq_spread_out", "Payments 11+ minutes ago are outside the window",
    baseline(100) + [tx(100, m) for m in (11, 12, 13, 14)], tx(100), {}, "LOW")
add("freq_exactly_10_min_is_counted", "A payment exactly 10 minutes ago is inside the window",
    baseline(100) + [tx(100, 10), tx(100, 9)], tx(100), {"High frequency": 15}, "LOW")
add("freq_same_timestamp", "Payments with the same timestamp count",
    baseline(100) + [tx(100, 0), tx(100, 0)], tx(100), {"High frequency": 15}, "LOW")

# =================== 3. SPENDING CHANGE ===================
add("spend_2_8x_below_rule", "2.8x the daily spending is below the 3x rule",
    baseline(500), tx(1400), {}, "LOW")
add("spend_spike_only", "Many normal-size payments in one day -> only spending rule fires (+20)",
    baseline(500) + [tx(400, m) for m in (60, 120, 180, 240)], tx(400),
    {"Spending change": 20}, "LOW")
add("spend_under_1000_not_checked", "Total under 1000 is ignored even if the ratio is high",
    baseline(100) + [tx(150, m) for m in (60, 120, 180, 240)], tx(150), {}, "LOW")
add("spend_exactly_1000_is_checked", "Total of exactly 1000 is checked",
    baseline(100) + [tx(250, m) for m in (60, 120, 180)], tx(250), {"Spending change": 20}, "LOW")
add("spend_failed_payment_not_spending", "A failed payment is not money spent (amount rule still sees it)",
    baseline(100), tx(3000, status="failed"), {"High amount": 30}, "MEDIUM")
add("spend_no_earlier_week_history", "No payments in the 7 days before today -> nothing to compare",
    [tx(400, m) for m in (60, 120, 180)], tx(400), {}, "LOW")
add("spend_short_history_uses_real_days", "3 days of history: divide by 3, not 7",
    [tx(1000, d * DAY) for d in (2, 3, 4)], tx(1500), {}, "LOW")

# =================== 4. LOCATION ===================
add("loc_known_city", "Usual city, nothing fires",
    baseline(100), tx(100, location="Chennai"), {}, "LOW")
add("loc_new_city", "City never used before -> +15",
    baseline(100), tx(100, location="Paris"), {"New location": 15}, "LOW")
add("loc_case_and_spaces", "'  CHENNAI ' is the same as 'chennai'",
    baseline(100), tx(100, location="  CHENNAI "), {}, "LOW")
add("loc_missing_none", "Missing location (None) does not crash",
    baseline(100), tx(100, location=None), {}, "LOW")
add("loc_missing_empty_string", "Empty location is treated as missing",
    baseline(100), tx(100, location=""), {}, "LOW")
add("loc_missing_only_spaces", "Location with only spaces is treated as missing",
    baseline(100), tx(100, location="   "), {}, "LOW")
add("loc_too_little_history", "2 past payments: new-location rule is skipped",
    [tx(100, 2 * DAY), tx(100, 3 * DAY)], tx(100, location="Paris"), {}, "LOW")
add("loc_seen_only_in_failed_payment", "A city seen only in a failed payment is still new",
    baseline(100) + [tx(100, 3 * DAY + 30, "Paris", "failed")],
    tx(100, location="Paris"), {"New location": 15}, "LOW")
add("loc_second_known_city", "A second city the customer already uses is fine",
    baseline(100) + [tx(100, 3 * DAY + 30, "Bengaluru")], tx(100, location="Bengaluru"), {}, "LOW")
add("loc_history_without_locations", "Old payments had no location -> nothing to compare against",
    [tx(100, d * DAY + 120, location=None) for d in range(2, 7)],
    tx(100, location="Chennai"), {}, "LOW")

# ---- location changed too fast ----
add("fast_59_min", "Chennai then Delhi 59 minutes later -> +20",
    TWO_CITIES + [tx(100, 59)], tx(100, location="Delhi"), {"Fast location change": 20}, "LOW")
add("fast_exactly_60_min", "Exactly 60 minutes is still 'too fast'",
    TWO_CITIES + [tx(100, 60)], tx(100, location="Delhi"), {"Fast location change": 20}, "LOW")
add("fast_61_min", "61 minutes is not flagged",
    TWO_CITIES + [tx(100, 61)], tx(100, location="Delhi"), {}, "LOW")
add("fast_same_city", "Same city again 10 minutes later is fine",
    TWO_CITIES + [tx(100, 10)], tx(100, location="Chennai"), {}, "LOW")
add("fast_last_location_missing", "Last payment had no location -> cannot compare",
    TWO_CITIES + [tx(100, 10, location=None)], tx(100, location="Delhi"), {}, "LOW")
add("fast_failed_payment_counts_as_last_place", "A failed payment still shows where the card was used",
    TWO_CITIES + [tx(100, 10, "Chennai", "failed")], tx(100, location="Delhi"),
    {"Fast location change": 20}, "LOW")
add("fast_and_new_city_together", "New city AND fast change -> 15 + 20",
    baseline(100) + [tx(100, 20)], tx(100, location="London"),
    {"New location": 15, "Fast location change": 20}, "MEDIUM")

# =================== 5. FAILED ATTEMPTS ===================
add("failed_1", "A single failed payment is normal",
    baseline(100), tx(100, status="failed"), {}, "LOW")
add("failed_2", "2 failed payments in 30 minutes -> +15",
    baseline(100) + [tx(100, 5, status="failed")], tx(100, status="failed"),
    {"Failed attempts": 15}, "LOW")
add("failed_3_spread_out", "3 failed payments in 30 minutes -> +30",
    baseline(100) + [tx(100, 20, status="failed"), tx(100, 25, status="failed")],
    tx(100, status="failed"), {"Failed attempts": 30}, "MEDIUM")
add("failed_3_then_success", "3 failures before a successful payment (card testing)",
    baseline(100) + [tx(100, m, status="failed") for m in (20, 22, 24)], tx(100),
    {"Failed attempts": 30}, "MEDIUM")
add("failed_outside_30_min", "Failures older than 30 minutes are ignored",
    baseline(100) + [tx(100, m, status="failed") for m in (31, 32, 33)], tx(100), {}, "LOW")
add("failed_exactly_30_min_counted", "A failure exactly 30 minutes ago is inside the window",
    baseline(100) + [tx(100, 30, status="failed"), tx(100, 29, status="failed")],
    tx(100, status="failed"), {"Failed attempts": 30}, "MEDIUM")

# =================== 6. COMBINED PATTERNS ===================
add("combo_full_attack_capped_at_100", "Every rule except fast-change fires: 125 points is capped at 100",
    baseline(500) + [tx(600, 9)] + [tx(5000, m, "Moscow", "failed") for m in (4, 3, 2)],
    tx(90000, location="Moscow"),
    {"High amount": 35, "High frequency": 25, "Spending change": 20,
     "New location": 15, "Failed attempts": 30}, "HIGH")
add("combo_exactly_60_is_high", "30 + 30 = 60 is the HIGH boundary",
    baseline(100) + [tx(100, 20, status="failed"), tx(100, 22, status="failed")],
    tx(500, status="failed"), {"High amount": 30, "Failed attempts": 30}, "HIGH")
add("combo_account_takeover", "Huge payment in a new country right after a home payment",
    baseline(500) + [tx(600, 12)], tx(60000, location="Lagos"),
    {"High amount": 35, "Spending change": 20, "New location": 15, "Fast location change": 20}, "HIGH")
add("combo_card_testing", "3 small failures then a success",
    baseline(300) + [tx(50, m, status="failed") for m in (6, 4, 2)], tx(600),
    {"High frequency": 15, "Failed attempts": 30}, "MEDIUM")
add("combo_burst_of_seven", "7 payments in 6 minutes",
    baseline(300) + [tx(300, m) for m in (1, 2, 3, 4, 5, 6)], tx(300),
    {"High frequency": 25, "Spending change": 20}, "MEDIUM")

# =================== 7. DATA / ORDER EDGE CASES ===================
add("data_future_payments_ignored", "A payment that happens AFTER the new one must not be used",
    baseline(100) + [tx(5000, -30, "Paris")], tx(100), {}, "LOW")
add("data_unsorted_history", "History given in random order gives the same answer",
    list(reversed(baseline(100) + [tx(100, 20, status="failed"), tx(100, 25, status="failed")])),
    tx(100, status="failed"), {"Failed attempts": 30}, "MEDIUM")
add("data_tiny_amount_no_location", "Tiny amount and no location for a new customer",
    [], tx(0.01, location=None), {}, "LOW")
