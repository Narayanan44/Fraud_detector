# Approach

This document explains how the fraud / anomaly detection engine works and why I made each decision.

## 1. Problem

A payment system receives many transactions. A few are fraud (stolen card, card testing, account takeover). A person cannot check every one, so the system must:

1. take a new transaction (user, amount, location, status, time),
2. compare it with **that customer's own** past behaviour,
3. give a **risk score from 0 to 100**,
4. **explain the reasons** in plain words, because a fraud analyst needs to know why a payment was flagged.

The five signals asked for are: unusually high amounts, high transaction frequency, sudden spending changes, unusual location, and multiple failed transactions.

## 2. Why rule-based scoring

I used rules that add points. I did not use machine learning.

- **Explainable.** Every point comes from a rule that can be read in one function. The reason text is created by the same code that gives the points.
- **No labelled data needed.** Real fraud data is private and rare. A model needs many labelled fraud examples to learn from.
- **Each customer is compared with themselves.** A payment of 5000 is normal for one customer and suspicious for another. Rules that use the customer's own history handle this directly.
- **Easy to change.** Thresholds are constants at the top of `risk_engine.py`. A new rule is one new function plus one line in the `RULES` list.

I also considered a z-score (mean and standard deviation) and an anomaly model such as Isolation Forest. I did not use them because they are harder to explain to a non-technical reader, and they behave badly when a customer has only a few payments.

## 2.1 How a request flows

```
POST /transactions
  1. validate the input (amount > 0, user not empty, status is success/failed)
  2. load this customer's payments from the last 30 days (up to this payment's time)
  3. risk_engine.calculate_risk(payment, history)
  4. save the payment with its score, level and reasons
  5. return the result
```

`risk_engine.py` has no database or web code. It receives plain Python values and returns a result, which makes it easy to test.

## 3. How the score is calculated

`calculate_risk(txn, user_history)` does four steps:

1. **Prepare history.** Keep only the customer's payments that happened at or before this payment, and sort them oldest first. Future payments are never used.
2. **Make "good history".** This is the successful payments only. Failed payments are not normal behaviour, so they are not used as a baseline for amounts or locations.
3. **Run every rule.** Each rule returns `(points, message)`. Rules that give 0 points are left out of the reasons.
4. **Add the points.** The total is capped at 100. Level: **0-29 LOW, 30-59 MEDIUM, 60+ HIGH**.

If the customer has fewer than 3 successful payments, the result also contains an information line "Not enough history" (0 points). If nothing fires, the reason is "No suspicious behaviour found". So there is always an explanation.

All rules have the same shape, which is why a new rule is easy to add:

```python
def check_something(txn, history, good_history):
    ...
    return points, message      # (0, None) if nothing is wrong

RULES = [("High amount", check_high_amount), ...]
```

## 4. The rules

### 4.1 High amount (20 / 30 / 35)

- **Relative check:** compare the amount with the **median** of the customer's past successful amounts. 3x or more gives 20 points, 5x or more gives 30 points.
- **Fixed check:** an amount of 50,000 or more gives 35 points. This works even for a brand new customer.
- The bigger of the two is used. They are **not** added, so one big payment is not punished twice for the same reason.

Why the median and not the average: one old large purchase raises the average a lot and could hide a later fraud. The median is not affected by a few outliers.
The relative check needs at least 3 successful payments in history.

### 4.2 High frequency (15 / 25)

Count the payments (any status) in the last 10 minutes, including the new one. 3 or 4 gives 15 points, 5 or more gives 25 points.
A payment exactly 10 minutes ago is counted. This rule needs no history, so it also works for new customers.

### 4.3 Sudden spending change (20)

- Spending in the last 24 hours (successful payments only, including the new one if it succeeded).
- Compared with the **usual daily spending**: the total of successful payments from 8 days ago to 1 day ago, divided by the number of days that history really covers (between 1 and 7).
- If the 24-hour spending is 3x or more the usual daily spending, add 20 points.

Edge cases:
- If the customer has no payments in that earlier week, the rule is skipped (nothing to compare).
- If the 24-hour spending is under 1,000, the rule is skipped. Without this, going from 10 to 40 rupees would be called a "spike".
- A failed payment is not money spent, so it is not counted.
- **Bug found while testing:** at first I always divided by 7. A new customer with only 2 days of history had a very low "usual daily spending", so normal payments looked like spikes. Now the code divides by the days actually covered.

### 4.4 Unusual location (15 and 20)

Two separate rules:

- **New location (15):** the city was never used in the customer's successful history. Needs at least 3 successful payments. A city seen only in a failed payment still counts as new. Payments with no location are ignored.
- **Fast location change (20):** the customer's previous payment (any status) was in a different city 60 minutes or less before. A failed payment still shows where the card was used, so it counts.

Locations are cleaned before comparing, so `"  CHENNAI "` and `"chennai"` are the same. A missing location (None, empty or only spaces) skips both rules.
**Bug found while testing:** if the old payments had no location, the empty text was treated as a "known place", so the first payment with a location was wrongly called a new location. Empty locations are now ignored, and if no location is known the rule is skipped.

### 4.5 Failed transactions (15 / 30)

Count failed payments in the last 30 minutes (plus the new payment if it failed). 2 gives 15 points, 3 or more gives 30 points.
A success after several failures is also flagged (a typical card-testing pattern). Failures older than 30 minutes are ignored. This rule needs no history.

### Points summary

| Rule | Condition | Points |
|---|---|---|
| High amount | 3x / 5x the median, or 50,000+ | 20 / 30 / 35 |
| High frequency | 3-4 / 5+ payments in 10 min | 15 / 25 |
| Spending change | 24h spending 3x the usual daily spending | 20 |
| New location | city never used | 15 |
| Fast location change | different city within 60 min | 20 |
| Failed attempts | 2 / 3+ failures in 30 min | 15 / 30 |

The maximum possible total is 145, which is capped at 100.
The point values are my own judgement: patterns that are stronger evidence of fraud (a huge payment, repeated failures) get more points than weaker ones (a new city alone). Two weak signals together reach MEDIUM (for example 15 + 20 = 35), and two strong ones reach HIGH (for example 30 + 30 = 60).

## 5. Edge cases handled

| Situation | What happens |
|---|---|
| New customer (no history) | Only the rules that need no history run: fixed amount limit, frequency, failed attempts. The result says "Not enough history". |
| Only 1-2 past payments | Treated like a new customer for history-based rules, because 2 payments are too few to compare. |
| History has only failed payments | No baseline exists, same as a new customer. |
| Amount 0, negative, "abc", infinity, missing | Rejected with status 422. |
| Empty or only-spaces user id | Rejected. Spaces around a user id are trimmed. |
| Status other than success/failed | Rejected. |
| Missing time | The current time is used. |
| Time with a timezone | The timezone is removed so all times can be compared. |
| Payment arrives late (older time) | It is scored using only payments up to its own time. Later payments are not used. |
| Payments older than 30 days | Not loaded as history. |
| History not sorted | The engine sorts it first. |
| Several payments with the same timestamp | All are counted for frequency. |
| Median amount is 0 | No division by zero; the relative check is skipped. |
| Missing or blank location | Location rules are skipped, nothing crashes. |
| Case and spaces in city names | Ignored when comparing. |
| Very large amount (1e12) / very small amount (0.01) | Both work. |
| Many rules fire at once | Score is capped at 100. |
| Score exactly on a level boundary | 29 is LOW, 30 is MEDIUM, 59 is MEDIUM, 60 is HIGH. |

## 6. Testing

I wanted the tests to cover the exact edges, not only the normal cases.

- **59 scenarios** in `tests/engine_cases.py`. For each one I worked out the expected points by hand from the rules **before** running the code. Each scenario is checked three ways: right rules and points, a well-formed result, and the input data not being changed. That is 177 tests, plus 6 for the level boundaries.
- **Boundary cases** such as 2.9x vs 3x, 4.9x vs 5x, 59 / 60 / 61 minutes, a payment exactly 10 or 30 minutes ago, and a spending total under 1000 vs exactly 1000.
- **18 basic tests** for each rule.
- **32 API tests** for validation, history kept between requests, the 30-day window, late payments, filtering and deleting. They use a separate SQLite file.
- **8 dataset tests** check the CSV (size, valid values), replay it through the engine, and confirm that all three levels appear and every rule fires.
- **10 manual test payments** (`MANUAL_TESTS.md`, `run_manual_tests.py`) that can be run against the local or the deployed backend.

Total: **241 automated tests**. The two bugs mentioned in section 4 were found by these tests and by replaying the sample data.

## 7. Sample dataset

The dataset is **synthetic**, created by `generate_sample_data.py` with a fixed random seed, so it is always the same.

- 826 payments, 36 customers, 12 days (28 Sep to 9 Oct 2026), 14 cities, 80 failed payments.
- **30 repeat customers** (19-35 payments each). They have 1 to 3 payments per day in the morning, afternoon or evening, in a home city and sometimes a second city. This gives each of them a real history.
- **24 of them also have 2-3 incidents** on different days: failed attempts then a huge payment abroad, account takeover, burst of 7 payments in 6 minutes, 5 big purchases in one day, home city to abroad within minutes, card testing, a payment 30x the usual, and a payment 4x the usual in a new city.
- **6 new customers** with 2 to 6 payments to test the new-customer checks (huge first payment, normal first payments, quick failures, a burst).
- A few **harmless unusual** cases (travel to another city 9 hours later, a payment 2.5x the usual) to check for false alarms.

Replaying the dataset through the engine gives 688 LOW, 90 MEDIUM and 48 HIGH. All 569 ordinary payments stay LOW. The share of fraud here is far higher than in real life. I did this on purpose so that every rule and level can be seen in a demo. In real data fraud is rare, so false alarms (precision) would matter much more.

## 8. Limitations and what I would do next

- **Locations are text.** Real distance and travel speed (impossible travel) need coordinates.
- **Thresholds are hand-picked** and checked only on synthetic data. With real labelled data I would tune them and measure precision and recall.
- **A late payment does not re-score the later ones.** A background job could fix that.
- **The fixed limit (50,000) is the same for everyone and in one currency.** It could depend on the account type.
- **No authentication and no pagination** on the list endpoint.
- **More signals** such as device, merchant type or time of day could be added as new rules without changing the existing ones.
- **A hybrid approach:** keep these rules for explanations and add a trained model (for example Isolation Forest) as one more score when enough labelled data exists.

## 9. Technology

| Part | Choice | Reason |
|---|---|---|
| Backend | Python + FastAPI | Simple, automatic input validation and API docs |
| Database | PostgreSQL (SQLite as a local default) | Same code for both through SQLAlchemy |
| Frontend | React + Vite | Small dashboard with a form, summary counts and a table of reasons |
| Tests | Pytest | Data-driven tests for many cases |
