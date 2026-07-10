# build_database.py
# Sets up the SQLite database for the bank app behavioural analysis project
# and fills it with realistic (randomly generated but seeded) sample data.
#
# Run this ONCE to create bank_app.db. After that, use analysis.py to run
# the actual SQL tasks against it.

import sqlite3
import random
from datetime import datetime, timedelta

random.seed(42)  # keeping this fixed so the data is the same every time we run it

DB_NAME = "bank_app.db"

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

# wipe any old tables first in case we run this more than once
cur.executescript("""
DROP TABLE IF EXISTS feature_usage;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS login_activity;
DROP TABLE IF EXISTS customers;
""")

# -----------------------------------------------------------------
# CUSTOMERS TABLE
# -----------------------------------------------------------------
cur.execute("""
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    age INTEGER,
    gender TEXT,
    province TEXT,
    account_type TEXT,
    signup_date TEXT
)
""")

provinces = ["Gauteng", "Western Cape", "KZN", "Eastern Cape", "Limpopo", "Free State"]
account_types = ["Standard", "Premium"]

customers = []
for i in range(1001, 1081):  # 80 customers, small but enough to show real patterns
    age = random.randint(19, 65)
    gender = random.choice(["Male", "Female"])
    province = random.choice(provinces)
    # premium accounts weighted a bit lower, feels more realistic
    account_type = random.choices(account_types, weights=[0.7, 0.3])[0]
    # signup spread between Nov 2025 and Apr 2026
    signup = datetime(2025, 11, 1) + timedelta(days=random.randint(0, 150))
    customers.append((i, age, gender, province, account_type, signup.strftime("%Y-%m-%d")))

cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?)", customers)

# -----------------------------------------------------------------
# LOGIN ACTIVITY TABLE
# -----------------------------------------------------------------
cur.execute("""
CREATE TABLE login_activity (
    login_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    login_date TEXT,
    session_minutes INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
)
""")

# reference "today" for this dataset - pretend we pulled this on 30 June 2026
DATA_END = datetime(2026, 6, 30)

# split customers into rough behaviour groups so the churn/dormant analysis
# actually has something interesting to find later
# ~15% never really engaged (a handful of logins right after signup, then nothing)
# ~15% dormant (were active, stopped logging in more than 60 days ago)
# rest are regular ongoing users with varying frequency
customer_ids = [c[0] for c in customers]
random.shuffle(customer_ids)
never_engaged = set(customer_ids[:12])
dormant = set(customer_ids[12:24])
# everyone else stays "active"

login_id = 1
logins = []
for cust in customers:
    cid, age, gender, province, acc_type, signup_str = cust
    signup = datetime.strptime(signup_str, "%Y-%m-%d")

    if cid in never_engaged:
        # only 1-3 logins total, all shortly after signup
        n_logins = random.randint(1, 3)
        for _ in range(n_logins):
            day_offset = random.randint(0, 14)
            login_date = signup + timedelta(days=day_offset)
            if login_date > DATA_END:
                continue
            logins.append((login_id, cid, login_date.strftime("%Y-%m-%d"), random.randint(2, 8)))
            login_id += 1

    elif cid in dormant:
        # active for a while, then just stopped - last login more than 60 days before DATA_END
        stop_date = DATA_END - timedelta(days=random.randint(65, 150))
        active_window = (stop_date - signup).days
        if active_window < 5:
            active_window = 5
        n_logins = random.randint(8, 25)
        for _ in range(n_logins):
            day_offset = random.randint(0, active_window)
            login_date = signup + timedelta(days=day_offset)
            logins.append((login_id, cid, login_date.strftime("%Y-%m-%d"), random.randint(3, 25)))
            login_id += 1

    else:
        # regular ongoing user, logs in fairly consistently right up to DATA_END
        active_window = (DATA_END - signup).days
        n_logins = random.randint(20, 60)
        for _ in range(n_logins):
            day_offset = random.randint(0, active_window)
            login_date = signup + timedelta(days=day_offset)
            logins.append((login_id, cid, login_date.strftime("%Y-%m-%d"), random.randint(3, 30)))
            login_id += 1

cur.executemany("INSERT INTO login_activity VALUES (?,?,?,?)", logins)

# -----------------------------------------------------------------
# TRANSACTIONS TABLE
# -----------------------------------------------------------------
cur.execute("""
CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    transaction_date TEXT,
    amount REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
)
""")

# roughly half of all logins result in some kind of transaction that day
# premium customers transact bigger amounts on average
txn_id = 1001
transactions = []
cust_lookup = {c[0]: c for c in customers}

for l in logins:
    _, cid, login_date, _ = l
    if random.random() < 0.45:
        acc_type = cust_lookup[cid][4]
        if acc_type == "Premium":
            amount = round(random.uniform(500, 15000), 2)
        else:
            amount = round(random.uniform(50, 3000), 2)
        transactions.append((txn_id, cid, login_date, amount))
        txn_id += 1

cur.executemany("INSERT INTO transactions VALUES (?,?,?,?)", transactions)

# -----------------------------------------------------------------
# FEATURE USAGE TABLE
# -----------------------------------------------------------------
cur.execute("""
CREATE TABLE feature_usage (
    usage_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    feature_name TEXT,
    usage_date TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
)
""")

# weighting features so Transfer Money and Buy Airtime dominate, Investments
# and Loan Applications are rarer - matches what the brief described
features = ["Transfer Money", "Buy Airtime", "Pay Bills", "Investments", "Loan Applications"]
feature_weights = [0.40, 0.25, 0.20, 0.08, 0.07]

usage_id = 1
usage_rows = []
for l in logins:
    _, cid, login_date, _ = l
    # not every login triggers a feature use, sometimes people just check balance
    n_features_used = random.choices([0, 1, 2], weights=[0.2, 0.6, 0.2])[0]
    used_today = random.sample(features, k=min(n_features_used, len(features))) if n_features_used else []
    for feat in used_today[:n_features_used]:
        usage_rows.append((usage_id, cid, feat, login_date))
        usage_id += 1

# top up with weighted random usage so the popularity ranking looks realistic
# (the sampling above doesn't respect weights, so add extra weighted rows)
extra_rows = []
for l in random.sample(logins, k=int(len(logins) * 0.6)):
    _, cid, login_date, _ = l
    feat = random.choices(features, weights=feature_weights)[0]
    extra_rows.append((usage_id, cid, feat, login_date))
    usage_id += 1
usage_rows.extend(extra_rows)

cur.executemany("INSERT INTO feature_usage VALUES (?,?,?,?)", usage_rows)

conn.commit()

print(f"Database built: {DB_NAME}")
print(f"Customers: {len(customers)}")
print(f"Logins: {len(logins)}")
print(f"Transactions: {len(transactions)}")
print(f"Feature usage rows: {len(usage_rows)}")

conn.close()
