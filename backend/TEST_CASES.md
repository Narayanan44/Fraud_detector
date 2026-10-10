# Test cases

- **Engine scenarios:** 59 (each one is checked 3 ways: expected rules and points, valid output, input not modified)
- **Level boundaries:** 0, 29, 30, 59, 60, 100
- **Sample dataset checks:** size, valid values, all levels appear, every rule fires
- **API checks:** see the last table

Run all tests: `pytest` (from the `backend` folder). Run one case: `pytest -k amount_5x_boundary`

## 1. High amount

| Case | What it proves | Expected points | Level |
|---|---|---|---|
| `amount_normal` | Normal payment, nothing fires | nothing fires (score 0) | LOW |
| `amount_2_9x_below_rule` | 2.9x the usual amount is below the 3x rule | nothing fires (score 0) | LOW |
| `amount_3x_boundary` | Exactly 3x the usual amount -> +20 | High amount +20 (score 20) | LOW |
| `amount_4_9x` | 4.9x is still the 3x level -> +20 | High amount +20 (score 20) | LOW |
| `amount_5x_boundary` | Exactly 5x -> +30 (score 30 is the MEDIUM boundary) | High amount +30 (score 30) | MEDIUM |
| `amount_100x_also_spending` | 100x the usual: amount +30 and daily spending +20 | High amount +30, Spending change +20 (score 50) | MEDIUM |
| `amount_exactly_fixed_limit_new_customer` | No history, exactly 50000 -> fixed limit +35 | High amount +35 (score 35) | MEDIUM |
| `amount_fixed_and_ratio_not_added` | Fixed limit (35) and ratio (30) both apply, only the bigger counts | High amount +35, Spending change +20 (score 55) | MEDIUM |
| `amount_new_customer_small` | New customer, small payment, nothing fires | nothing fires (score 0) | LOW |
| `amount_only_two_past_payments` | 2 past payments are too few to compare, 5000 is under the fixed limit | nothing fires (score 0) | LOW |
| `amount_failed_history_is_no_baseline` | Failed payments are not normal behaviour, so no baseline exists | nothing fires (score 0) | LOW |
| `amount_history_of_zero_does_not_crash` | Median of 0 must not cause a divide by zero | nothing fires (score 0) | LOW |
| `amount_huge_new_customer` | Huge number (1e12) works and only fixed limit fires | High amount +35 (score 35) | MEDIUM |

## 2. High frequency

| Case | What it proves | Expected points | Level |
|---|---|---|---|
| `freq_2_in_10_min` | 2 payments in 10 minutes is normal | nothing fires (score 0) | LOW |
| `freq_3_in_10_min` | 3 payments in 10 minutes -> +15 | High frequency +15 (score 15) | LOW |
| `freq_4_in_10_min` | 4 payments still the +15 level | High frequency +15 (score 15) | LOW |
| `freq_5_in_10_min` | 5 payments -> +25 | High frequency +25 (score 25) | LOW |
| `freq_6_in_10_min` | 6 payments is still +25 (no extra points) | High frequency +25 (score 25) | LOW |
| `freq_spread_out` | Payments 11+ minutes ago are outside the window | nothing fires (score 0) | LOW |
| `freq_exactly_10_min_is_counted` | A payment exactly 10 minutes ago is inside the window | High frequency +15 (score 15) | LOW |
| `freq_same_timestamp` | Payments with the same timestamp count | High frequency +15 (score 15) | LOW |

## 3. Sudden spending change

| Case | What it proves | Expected points | Level |
|---|---|---|---|
| `spend_2_8x_below_rule` | 2.8x the daily spending is below the 3x rule | nothing fires (score 0) | LOW |
| `spend_spike_only` | Many normal-size payments in one day -> only spending rule fires (+20) | Spending change +20 (score 20) | LOW |
| `spend_under_1000_not_checked` | Total under 1000 is ignored even if the ratio is high | nothing fires (score 0) | LOW |
| `spend_exactly_1000_is_checked` | Total of exactly 1000 is checked | Spending change +20 (score 20) | LOW |
| `spend_failed_payment_not_spending` | A failed payment is not money spent (amount rule still sees it) | High amount +30 (score 30) | MEDIUM |
| `spend_no_earlier_week_history` | No payments in the 7 days before today -> nothing to compare | nothing fires (score 0) | LOW |
| `spend_short_history_uses_real_days` | 3 days of history: divide by 3, not 7 | nothing fires (score 0) | LOW |

## 4a. Unusual location (new city)

| Case | What it proves | Expected points | Level |
|---|---|---|---|
| `loc_known_city` | Usual city, nothing fires | nothing fires (score 0) | LOW |
| `loc_new_city` | City never used before -> +15 | New location +15 (score 15) | LOW |
| `loc_case_and_spaces` | '  CHENNAI ' is the same as 'chennai' | nothing fires (score 0) | LOW |
| `loc_missing_none` | Missing location (None) does not crash | nothing fires (score 0) | LOW |
| `loc_missing_empty_string` | Empty location is treated as missing | nothing fires (score 0) | LOW |
| `loc_missing_only_spaces` | Location with only spaces is treated as missing | nothing fires (score 0) | LOW |
| `loc_too_little_history` | 2 past payments: new-location rule is skipped | nothing fires (score 0) | LOW |
| `loc_seen_only_in_failed_payment` | A city seen only in a failed payment is still new | New location +15 (score 15) | LOW |
| `loc_second_known_city` | A second city the customer already uses is fine | nothing fires (score 0) | LOW |
| `loc_history_without_locations` | Old payments had no location -> nothing to compare against | nothing fires (score 0) | LOW |

## 4b. Location changed too fast

| Case | What it proves | Expected points | Level |
|---|---|---|---|
| `fast_59_min` | Chennai then Delhi 59 minutes later -> +20 | Fast location change +20 (score 20) | LOW |
| `fast_exactly_60_min` | Exactly 60 minutes is still 'too fast' | Fast location change +20 (score 20) | LOW |
| `fast_61_min` | 61 minutes is not flagged | nothing fires (score 0) | LOW |
| `fast_same_city` | Same city again 10 minutes later is fine | nothing fires (score 0) | LOW |
| `fast_last_location_missing` | Last payment had no location -> cannot compare | nothing fires (score 0) | LOW |
| `fast_failed_payment_counts_as_last_place` | A failed payment still shows where the card was used | Fast location change +20 (score 20) | LOW |
| `fast_and_new_city_together` | New city AND fast change -> 15 + 20 | New location +15, Fast location change +20 (score 35) | MEDIUM |

## 5. Multiple failed transactions

| Case | What it proves | Expected points | Level |
|---|---|---|---|
| `failed_1` | A single failed payment is normal | nothing fires (score 0) | LOW |
| `failed_2` | 2 failed payments in 30 minutes -> +15 | Failed attempts +15 (score 15) | LOW |
| `failed_3_spread_out` | 3 failed payments in 30 minutes -> +30 | Failed attempts +30 (score 30) | MEDIUM |
| `failed_3_then_success` | 3 failures before a successful payment (card testing) | Failed attempts +30 (score 30) | MEDIUM |
| `failed_outside_30_min` | Failures older than 30 minutes are ignored | nothing fires (score 0) | LOW |
| `failed_exactly_30_min_counted` | A failure exactly 30 minutes ago is inside the window | Failed attempts +30 (score 30) | MEDIUM |

## 6. Combined patterns

| Case | What it proves | Expected points | Level |
|---|---|---|---|
| `combo_full_attack_capped_at_100` | Every rule except fast-change fires: 125 points is capped at 100 | High amount +35, High frequency +25, Spending change +20, New location +15, Failed attempts +30 (score 100) | HIGH |
| `combo_exactly_60_is_high` | 30 + 30 = 60 is the HIGH boundary | High amount +30, Failed attempts +30 (score 60) | HIGH |
| `combo_account_takeover` | Huge payment in a new country right after a home payment | High amount +35, Spending change +20, New location +15, Fast location change +20 (score 90) | HIGH |
| `combo_card_testing` | 3 small failures then a success | High frequency +15, Failed attempts +30 (score 45) | MEDIUM |
| `combo_burst_of_seven` | 7 payments in 6 minutes | High frequency +25, Spending change +20 (score 45) | MEDIUM |

## 7. Data and ordering edge cases

| Case | What it proves | Expected points | Level |
|---|---|---|---|
| `data_future_payments_ignored` | A payment that happens AFTER the new one must not be used | nothing fires (score 0) | LOW |
| `data_unsorted_history` | History given in random order gives the same answer | Failed attempts +30 (score 30) | MEDIUM |
| `data_tiny_amount_no_location` | Tiny amount and no location for a new customer | nothing fires (score 0) | LOW |

## API cases

| Request | Expected |
|---|---|
| amount = 0 | 422 rejected |
| amount = -50 | 422 rejected |
| amount missing / null / "abc" / "inf" | 422 rejected |
| user_id missing, empty, or only spaces | 422 rejected |
| status = "maybe" | 422 rejected |
| time = "yesterday" | 422 rejected |
| empty body {} | 422 rejected |
| only user_id + amount | 200, status defaults to success, location null |
| location empty or unicode (சென்னை) | 200, saved as given |
| user_id "  U1  " | 200, saved as "U1" |
| amount 0.01 / amount 1e12 | 200, scores 0 / 35 |
| time with timezone +05:30 | 200, stored without converting |
| time missing | 200, current time used |
| 3 normal payments, then 10x amount | High amount fires (history remembered) |
| two users | history is not shared between users |
| payments older than 30 days | ignored, 'Not enough history' |
| old payment arrives after a newer one | scored without looking at the future |
| 3 failed payments in 4 minutes | scores 0, 15, 45 |
| filter level=medium / LOW / HIGH / banana | case-insensitive, unknown level gives empty list |
| DELETE all | table empty |
| load sample data | every row saved, scores 0-100, all three levels present |
