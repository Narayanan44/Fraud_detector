"""
Creates sample_data/transactions.csv
Run:  python generate_sample_data.py

- 30 REPEAT users: about 25 normal payments each over 12 days (so their history is rich).
    - 6 are always clean
    - 24 also have 2-3 suspicious incidents on different days
- 6 NEW users: only 1-4 payments (to show the "new customer" basic checks)

random.seed(42) means we get the SAME data every time we run it.
"""
import csv
import random
from datetime import datetime, timedelta

random.seed(42)

INDIAN_CITIES = ["Chennai", "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Pune", "Kolkata", "Coimbatore"]
FOREIGN_CITIES = ["London", "Dubai", "Moscow", "Lagos", "Singapore", "New York"]

FIRST_DAY = datetime(2026, 9, 28)                                   # normal history starts here
LAST_DAY = datetime(2026, 10, 9)                                    # and ends here
INCIDENT_DAYS = [datetime(2026, 10, d) for d in range(3, 10)]       # suspicious things happen on these days

CLEAN_USERS = 6
INCIDENT_USERS = 24

# How many incidents of each kind (shared between the 24 incident users)
INCIDENT_COUNTS = {
    # mostly HIGH risk
    "full_attack": 10,         # failed attempts abroad, then a huge payment
    "account_takeover": 5,     # home payment, then abroad: 2 failures + huge payment
    "huge_abroad": 2,          # one huge payment abroad 20 minutes after a home payment
    # mostly MEDIUM risk
    "burst": 6,                # 7 payments in 6 minutes
    "spending_spike": 7,       # 5 big purchases in one day
    "location_hop": 10,        # home -> abroad -> another country in 35 minutes
    "card_testing": 8,         # 3 small failed payments, then a success
    "big_amount": 12,          # one payment 30x the usual
    "medium_big_amount": 6,    # 4x the usual amount in a city never used before
    # look odd but are NOT fraud (should stay LOW)
    "slow_travel": 2,          # other city but 9 hours later
    "slightly_big": 2,         # 2.5x the usual, below our 3x rule
}

# New customers (only a few payments)
NEW_USER_TYPES = ["new_huge_first", "new_huge_first", "new_normal", "new_two_then_big",
                  "new_failed_burst", "new_burst"]

rows = []                   # every transaction goes here
current_label = "normal"    # which scenario made the row (used only for checking, not saved in the CSV)


def add_row(user, amount, location, status, time):
    rows.append({"user_id": user, "amount": int(amount), "location": location,
                 "status": status, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "label": current_label})


def at(day, hour, minute=0):
    return day.replace(hour=hour, minute=minute, second=0)


def make_normal_history(user, home, work, typical, skip_days):
    """2-3 normal payments per day (morning / afternoon / evening). Skip the incident days."""
    day = FIRST_DAY
    while day <= LAST_DAY:
        if day not in skip_days:
            parts = random.sample(["morning", "afternoon", "evening"], random.choice([1, 2, 2, 3]))
            for part in parts:
                if part == "morning":
                    time = at(day, random.randint(8, 10), random.randint(0, 59))
                elif part == "afternoon":
                    time = at(day, random.randint(13, 15), random.randint(0, 59))
                else:
                    time = at(day, random.randint(18, 21), random.randint(0, 59))

                amount = typical * random.uniform(0.5, 1.5)                  # normal ups and downs
                location = work if random.random() < 0.15 else home           # sometimes the second city
                status = "failed" if random.random() < 0.03 else "success"    # one failure is normal
                add_row(user, amount, location, status, time)
        day += timedelta(days=1)


def run_incident(user, name, d, home, work, typical):
    h = random.randint(9, 14)              # start hour of the incident
    foreign = random.choice(FOREIGN_CITIES)
    other_foreign = random.choice([c for c in FOREIGN_CITIES if c != foreign])
    new_indian_city = random.choice([c for c in INDIAN_CITIES if c not in (home, work)])

    if name == "full_attack":
        add_row(user, typical, home, "success", at(d, h, 0))
        for m in (5, 6, 7):
            add_row(user, 4000, foreign, "failed", at(d, h, m))
        add_row(user, 90000, foreign, "success", at(d, h, 9))

    elif name == "account_takeover":
        add_row(user, typical, home, "success", at(d, h, 0))
        add_row(user, max(typical * 10, 5000), foreign, "failed", at(d, h, 10))
        add_row(user, max(typical * 10, 5000), foreign, "failed", at(d, h, 11))
        add_row(user, 60000, foreign, "success", at(d, h, 12))

    elif name == "huge_abroad":
        add_row(user, typical, home, "success", at(d, h, 0))
        add_row(user, 90000, foreign, "success", at(d, h, 20))

    elif name == "burst":
        for m in range(7):
            add_row(user, max(typical, 300), home, "success", at(d, h, m))

    elif name == "spending_spike":
        for i in range(5):
            add_row(user, max(typical * 3.5, 600), home, "success", at(d, h + i * 2, 0))

    elif name == "location_hop":
        add_row(user, typical, home, "success", at(d, h, 0))
        add_row(user, typical, foreign, "success", at(d, h, 20))
        add_row(user, typical, other_foreign, "success", at(d, h, 35))

    elif name == "card_testing":
        for m in (0, 2, 4):
            add_row(user, 50, home, "failed", at(d, h, m))
        add_row(user, typical * 2, home, "success", at(d, h, 7))

    elif name == "big_amount":
        add_row(user, max(typical * 30, 5000), home, "success", at(d, h, 0))

    elif name == "medium_big_amount":
        add_row(user, max(typical * 4, 1200), new_indian_city, "success", at(d, h, 0))

    elif name == "slow_travel":
        add_row(user, typical, home, "success", at(d, 9, 0))
        add_row(user, typical, new_indian_city, "success", at(d, 18, 0))

    elif name == "slightly_big":
        add_row(user, typical * 2.5, home, "success", at(d, h, 0))


def make_new_user(user, kind, home):
    d = random.choice(INCIDENT_DAYS[-2:])        # Oct 8 or 9
    if kind == "new_huge_first":                 # very first payment is huge
        add_row(user, random.randint(55000, 95000), home, "success", at(d, 2, 0))
        add_row(user, 300, home, "success", at(d, 4, 0))
    elif kind == "new_normal":                   # ordinary new customer
        for day, amount in ((7, 300), (8, 350), (9, 280)):
            add_row(user, amount, home, "success", at(datetime(2026, 10, day), 11, 0))
    elif kind == "new_two_then_big":             # 2 small payments, then a very large one
        add_row(user, 400, home, "success", at(datetime(2026, 10, 6), 11, 0))
        add_row(user, 450, home, "success", at(datetime(2026, 10, 7), 19, 0))
        add_row(user, 60000, home, "success", at(d, 11, 0))
    elif kind == "new_failed_burst":      # 3 quick failures, then a success
        for m in (0, 1, 2):
            add_row(user, 100, home, "failed", at(d, 15, m))
        add_row(user, 100, home, "success", at(d, 15, 4))
    elif kind == "new_burst":                    # 6 payments in 5 minutes
        for m in range(6):
            add_row(user, 200, home, "success", at(d, 16, m))


# ---------------- main part ----------------
incident_list = []
for incident_name, how_many in INCIDENT_COUNTS.items():
    incident_list = incident_list + [incident_name] * how_many
random.shuffle(incident_list)

incidents_of_user = [[] for _ in range(INCIDENT_USERS)]       # deal incidents to the 24 users
for i, incident_name in enumerate(incident_list):
    incidents_of_user[i % INCIDENT_USERS].append(incident_name)

kinds = ["clean"] * CLEAN_USERS + list(range(INCIDENT_USERS))   # a number means "incident user number"
random.shuffle(kinds)

for number, kind in enumerate(kinds, start=1):
    user = f"U{number:02d}"
    home = random.choice(INDIAN_CITIES)
    work = random.choice([c for c in INDIAN_CITIES if c != home])
    typical = random.choice([150, 300, 500, 800, 1200, 2000])
    my_incidents = [] if kind == "clean" else incidents_of_user[kind]
    my_days = random.sample(INCIDENT_DAYS, len(my_incidents))
    print(user, "REPEAT", my_incidents)

    current_label = "normal"
    make_normal_history(user, home, work, typical, skip_days=my_days)
    for incident_name, day in zip(my_incidents, my_days):
        current_label = incident_name
        run_incident(user, incident_name, day, home, work, typical)

for number, kind in enumerate(NEW_USER_TYPES, start=len(kinds) + 1):
    user = f"U{number:02d}"
    print(user, "NEW", [kind])
    current_label = kind
    make_new_user(user, kind, random.choice(INDIAN_CITIES))

rows.sort(key=lambda r: r["time"])

with open("sample_data/transactions.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["user_id", "amount", "location", "status", "time"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

print(f"Created {len(rows)} rows for {len(kinds) + len(NEW_USER_TYPES)} users")
