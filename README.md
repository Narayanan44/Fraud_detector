# Fraud / Anomaly Detection Engine

A small system that checks a payment against the customer's own history, gives it a **risk score from 0 to 100**, and **explains why**.

It looks for: unusually high amounts, many payments in a short time, sudden spending changes, unusual locations, and repeated failed payments.

## Live demo

| | Link |
|---|---|
| Frontend (dashboard) | `ADD_VERCEL_URL_HERE` |
| Backend API docs (Swagger) | `ADD_RENDER_URL_HERE/docs` |
| GitHub | `ADD_GITHUB_URL_HERE` |

> The backend runs on a free plan and goes to sleep when nobody uses it. The first request can take about a minute. Please open the API docs link once and wait, then use the dashboard.

## Screenshots

| | |
|---|---|
| ![Dashboard](screenshots/01-dashboard.png) | ![High risk reasons](screenshots/02-high-risk-reasons.png) |
| ![Check a payment](screenshots/03-check-result.png) | ![Swagger docs](screenshots/04-swagger-docs.png) |
| ![All tests passing](screenshots/05-pytest-241-passed.png) | ![Manual tests](screenshots/06-manual-tests.png) |

## Tech stack

| Part | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | PostgreSQL (SQLite is used automatically if no database URL is set) |
| Detection | Rule-based scoring (plain Python, no ML library) |
| Frontend | React + Vite |
| Tests | Pytest |

## How it works

```
React form --> POST /transactions --> FastAPI (main.py)
                                         |
              loads this customer's payments from the last 30 days
                                         |
              risk_engine.calculate_risk(payment, history)
                                         |
              score + level + reasons are saved in the database
                                         |
React shows the score and the reasons
```

The whole decision is made in one file, `backend/app/risk_engine.py`. It is plain Python (no database, no FastAPI), so it is easy to read and test. Details of every rule are in [APPROACH.md](APPROACH.md).

## Risk rules (short version)

| Rule | Points |
|---|---|
| High amount: 3x the usual amount / 5x the usual amount / above the fixed limit of 50,000 | 20 / 30 / 35 |
| High frequency: 3 or 5+ payments in 10 minutes | 15 / 25 |
| Sudden spending change: last 24 hours is 3x the usual daily spending | 20 |
| New location: city never used before | 15 |
| Fast location change: city changed within 60 minutes | 20 |
| Failed payments: 2 or 3+ in 30 minutes | 15 / 30 |

Total is capped at 100. **0-29 = LOW, 30-59 = MEDIUM, 60+ = HIGH.**
A new customer with no history is still checked with the rules that do not need history (fixed amount limit, frequency, failed payments), and the result says "Not enough history".

## Project structure

```
Fraud_detector/
  backend/
    app/
      main.py             API endpoints, saves payments
      risk_engine.py      all the fraud rules and the score
      models.py           database table
      database.py         database connection
    sample_data/
      transactions.csv    sample dataset (826 payments, 36 customers)
    tests/                pytest tests and test data
    generate_sample_data.py   creates transactions.csv
    run_manual_tests.py       runs 10 manual test payments against a running backend
    TEST_CASES.md             list of all test cases
    MANUAL_TESTS.md           the 10 manual test payments
    requirements.txt
  frontend/
    src/App.jsx           the dashboard
  docker-compose.yml      local PostgreSQL
  APPROACH.md             algorithm and reasoning
```

## Run it locally

You need Python 3 and Node.js.

**1. Backend**

```
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000` and the docs are at `http://localhost:8000/docs`.
By default it uses a local SQLite file (`fraud.db`), so nothing else is needed.

**2. Frontend** (new terminal)

```
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and click **Load sample data**.

**3. Optional: use PostgreSQL**

```
docker compose up -d
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fraud
uvicorn app.main:app --reload      # run inside backend/
```

## API

| Method | URL | What it does |
|---|---|---|
| GET | `/` | Check that the API is running |
| POST | `/transactions` | Add a payment, get its risk score and reasons |
| GET | `/transactions?level=HIGH` | List payments (newest first). `level` is optional: LOW, MEDIUM or HIGH |
| POST | `/load-sample` | Load the sample dataset |
| DELETE | `/transactions` | Delete all payments |

**Example**

```
POST /transactions
{"user_id": "U29", "amount": 300, "location": "London", "status": "success", "time": "2026-10-10T10:20:00"}
```

Response (shortened):

```json
{
  "user_id": "U29",
  "risk_score": 35,
  "risk_level": "MEDIUM",
  "reasons": [
    {"rule": "New location", "points": 15, "message": "New location 'London', customer never used it before"},
    {"rule": "Fast location change", "points": 20, "message": "Location changed from 'Kolkata' to 'London' in 20 minutes"}
  ]
}
```

`time` is optional (the current time is used if it is missing). `location` is optional. `status` is `success` or `failed`.
Bad input is rejected with status 422: amount must be above 0, user_id cannot be empty, status must be `success` or `failed`.

## Sample dataset

`backend/sample_data/transactions.csv` has **826 payments from 36 customers** (28 Sep to 9 Oct 2026), in 14 cities, with 80 failed payments.

- **30 repeat customers** have 19 to 35 payments each, so their history is meaningful.
- **6 new customers** have only 2 to 6 payments, to test the "new customer" checks.
- Most repeat customers also have a few suspicious incidents (huge payment abroad, burst of payments, card testing, and so on). A few customers do odd but harmless things (travel 9 hours later, a slightly bigger purchase) to check that the system does not raise false alarms.
- Replaying the dataset gives 688 LOW, 90 MEDIUM and 48 HIGH. All 569 ordinary payments stay LOW.

The data is **synthetic**. It is created by `generate_sample_data.py` with a fixed random seed, so the same file is produced every time. The fraud share is much higher than in real life on purpose, so that every rule and every risk level can be seen in the demo.

## Tests

```
cd backend
pytest
```

**241 tests** run in about a second:

| File | Tests | What it checks |
|---|---|---|
| `test_engine_cases.py` + `engine_cases.py` | 183 | 59 scenarios (boundaries like 2.9x vs 3x, 59 vs 60 minutes, missing data), each checked 3 ways, plus level boundaries |
| `test_risk_engine.py` | 18 | Basic rule tests |
| `test_api.py` | 32 | Bad input, history between requests, 30-day window, filter, delete, sample load |
| `test_sample_data.py` | 8 | Dataset size and quality, every rule fires, all three levels appear |

The tests use their own SQLite file (`test_api.db`), so your real database is never touched.
All test cases are listed in [backend/TEST_CASES.md](backend/TEST_CASES.md).

**10 manual test payments** (see [backend/MANUAL_TESTS.md](backend/MANUAL_TESTS.md)) can be run against a running backend, local or deployed:

```
python run_manual_tests.py                          # local
python run_manual_tests.py https://YOUR-BACKEND-URL # deployed
```

This script first deletes all payments and reloads the sample data.

## Limitations

- Locations are plain text (city names), so the system cannot measure the real distance between two places.
- The thresholds (3x, 5x, 60 minutes and so on) are chosen by hand and tested on synthetic data. With real labelled fraud data they should be tuned.
- If an old payment arrives late, it is scored correctly, but payments that came after it are not re-scored.
- No login or user accounts, and the full payment list is returned without pagination.
