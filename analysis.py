# analysis.py
# Behavioural Data Analysis - Bank Mobile App
# Runs the 10 SQL tasks from the consulting brief against bank_app.db
#
# Make sure build_database.py has been run first so bank_app.db exists.

import sqlite3
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

conn = sqlite3.connect("bank_app.db")

# small helper so I'm not repeating pd.read_sql_query everywhere
def run(query):
    return pd.read_sql_query(query, conn)


# reference date used for "how many days since last login" type questions
# in a real project this would just be CURRENT_DATE, but our sample data
# stops at 30 June 2026 so we anchor to that instead
TODAY = "2026-06-30"

# -----------------------------------------------------------------
# TASK 1: Active users per month
# -----------------------------------------------------------------
print("=" * 70)
print("TASK 1: ACTIVE USERS PER MONTH")
print("=" * 70)

q1 = """
SELECT
    strftime('%Y-%m', login_date) AS month,
    COUNT(DISTINCT customer_id) AS active_users
FROM login_activity
GROUP BY month
ORDER BY month;
"""
print(run(q1))

# -----------------------------------------------------------------
# TASK 2: Most popular features
# -----------------------------------------------------------------
print("\n" + "=" * 70)
print("TASK 2: MOST POPULAR FEATURES")
print("=" * 70)

q2 = """
SELECT
    feature_name,
    COUNT(*) AS uses
FROM feature_usage
GROUP BY feature_name
ORDER BY uses DESC;
"""
print(run(q2))

# -----------------------------------------------------------------
# TASK 3: Customer engagement (total minutes in app)
# -----------------------------------------------------------------
print("\n" + "=" * 70)
print("TASK 3: TOP 10 MOST ENGAGED CUSTOMERS (BY TOTAL MINUTES)")
print("=" * 70)

q3 = """
SELECT
    c.customer_id,
    c.province,
    c.account_type,
    SUM(l.session_minutes) AS total_minutes
FROM login_activity l
JOIN customers c ON c.customer_id = l.customer_id
GROUP BY c.customer_id
ORDER BY total_minutes DESC
LIMIT 10;
"""
print(run(q3))

# -----------------------------------------------------------------
# TASK 4: Behaviour by province
# -----------------------------------------------------------------
print("\n" + "=" * 70)
print("TASK 4: AVERAGE SESSION TIME BY PROVINCE")
print("=" * 70)

q4 = """
SELECT
    c.province,
    ROUND(AVG(l.session_minutes), 1) AS avg_session_minutes,
    COUNT(DISTINCT c.customer_id) AS customers
FROM login_activity l
JOIN customers c ON c.customer_id = l.customer_id
GROUP BY c.province
ORDER BY avg_session_minutes DESC;
"""
print(run(q4))

# -----------------------------------------------------------------
# TASK 5: Customer journey - what feature do people use next in a session
# -----------------------------------------------------------------
# Using LEAD() to see what feature a customer used right after another one,
# on the same day. This gives us the most common "next step" in the journey.
print("\n" + "=" * 70)
print("TASK 5: MOST COMMON NEXT FEATURE USED (JOURNEY ANALYSIS)")
print("=" * 70)

q5 = """
WITH ordered_usage AS (
    SELECT
        customer_id,
        feature_name,
        usage_date,
        usage_id,
        LEAD(feature_name) OVER (
            PARTITION BY customer_id, usage_date
            ORDER BY usage_id
        ) AS next_feature
    FROM feature_usage
)
SELECT
    feature_name AS current_feature,
    next_feature,
    COUNT(*) AS times_this_sequence_happened
FROM ordered_usage
WHERE next_feature IS NOT NULL
GROUP BY feature_name, next_feature
ORDER BY times_this_sequence_happened DESC
LIMIT 10;
"""
print(run(q5))

# -----------------------------------------------------------------
# TASK 6: Dormant customers (no login in the last 60 days)
# -----------------------------------------------------------------
print("\n" + "=" * 70)
print("TASK 6: DORMANT CUSTOMERS (NO LOGIN IN LAST 60 DAYS)")
print("=" * 70)

q6 = f"""
SELECT
    c.customer_id,
    c.province,
    c.account_type,
    MAX(l.login_date) AS last_login,
    CAST(julianday('{TODAY}') - julianday(MAX(l.login_date)) AS INTEGER) AS days_since_last_login
FROM customers c
LEFT JOIN login_activity l ON l.customer_id = c.customer_id
GROUP BY c.customer_id
HAVING days_since_last_login > 60 OR last_login IS NULL
ORDER BY days_since_last_login DESC;
"""
dormant_df = run(q6)
print(dormant_df)
print(f"\nTotal dormant customers: {len(dormant_df)}")

# -----------------------------------------------------------------
# TASK 7: High value customers (top 10% by total transaction value)
# -----------------------------------------------------------------
print("\n" + "=" * 70)
print("TASK 7: TOP 10% HIGHEST VALUE CUSTOMERS")
print("=" * 70)

q7 = """
WITH customer_value AS (
    SELECT
        customer_id,
        SUM(amount) AS total_value
    FROM transactions
    GROUP BY customer_id
),
ranked AS (
    SELECT
        customer_id,
        total_value,
        NTILE(10) OVER (ORDER BY total_value DESC) AS value_decile
    FROM customer_value
)
SELECT customer_id, ROUND(total_value, 2) AS total_value
FROM ranked
WHERE value_decile = 1
ORDER BY total_value DESC;
"""
print(run(q7))

# -----------------------------------------------------------------
# TASK 8: Feature adoption - time from signup to first Investments use
# -----------------------------------------------------------------
print("\n" + "=" * 70)
print("TASK 8: DAYS FROM SIGNUP TO FIRST 'INVESTMENTS' USE")
print("=" * 70)

q8 = """
WITH first_investment_use AS (
    SELECT
        customer_id,
        MIN(usage_date) AS first_use_date
    FROM feature_usage
    WHERE feature_name = 'Investments'
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.signup_date,
    f.first_use_date,
    CAST(julianday(f.first_use_date) - julianday(c.signup_date) AS INTEGER) AS days_to_adopt
FROM customers c
JOIN first_investment_use f ON f.customer_id = c.customer_id
ORDER BY days_to_adopt;
"""
adoption_df = run(q8)
print(adoption_df)
if len(adoption_df) > 0:
    print(f"\nAverage days to adopt Investments feature: {adoption_df['days_to_adopt'].mean():.1f}")
    print(f"Customers who have adopted Investments: {len(adoption_df)} out of 80 total")

# -----------------------------------------------------------------
# TASK 9: Churn behaviour - active vs dormant comparison
# -----------------------------------------------------------------
print("\n" + "=" * 70)
print("TASK 9: BEHAVIOUR COMPARISON - ACTIVE VS DORMANT CUSTOMERS")
print("=" * 70)

# tag each customer as active/dormant first based on the same 60-day rule as task 6,
# then compare their behaviour across logins, transactions and feature usage
q9 = f"""
WITH last_login_per_customer AS (
    SELECT
        customer_id,
        MAX(login_date) AS last_login
    FROM login_activity
    GROUP BY customer_id
),
customer_status AS (
    SELECT
        c.customer_id,
        CASE
            WHEN julianday('{TODAY}') - julianday(l.last_login) > 60 THEN 'Dormant'
            ELSE 'Active'
        END AS status
    FROM customers c
    JOIN last_login_per_customer l ON l.customer_id = c.customer_id
)
SELECT
    s.status,
    COUNT(DISTINCT s.customer_id) AS customers,
    ROUND(AVG(login_counts.n_logins), 1) AS avg_logins,
    ROUND(AVG(login_counts.avg_session), 1) AS avg_session_minutes,
    ROUND(AVG(COALESCE(txn_counts.n_txns, 0)), 1) AS avg_transactions,
    ROUND(AVG(COALESCE(usage_counts.n_features, 0)), 1) AS avg_feature_uses
FROM customer_status s
JOIN (
    SELECT customer_id, COUNT(*) AS n_logins, AVG(session_minutes) AS avg_session
    FROM login_activity GROUP BY customer_id
) login_counts ON login_counts.customer_id = s.customer_id
LEFT JOIN (
    SELECT customer_id, COUNT(*) AS n_txns
    FROM transactions GROUP BY customer_id
) txn_counts ON txn_counts.customer_id = s.customer_id
LEFT JOIN (
    SELECT customer_id, COUNT(*) AS n_features
    FROM feature_usage GROUP BY customer_id
) usage_counts ON usage_counts.customer_id = s.customer_id
GROUP BY s.status;
"""
print(run(q9))

# -----------------------------------------------------------------
# TASK 10: Executive dashboard dataset - pulling the pieces together
# -----------------------------------------------------------------
print("\n" + "=" * 70)
print("TASK 10: EXECUTIVE DASHBOARD SUMMARY")
print("=" * 70)

print("\n--- Active users by month ---")
print(run(q1))

print("\n--- Revenue (transaction value) by province ---")
q10_revenue = """
SELECT
    c.province,
    ROUND(SUM(t.amount), 2) AS total_revenue,
    COUNT(t.transaction_id) AS transaction_count
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
GROUP BY c.province
ORDER BY total_revenue DESC;
"""
print(run(q10_revenue))

print("\n--- Top features ---")
print(run(q2))

print(f"\n--- Dormant users: {len(dormant_df)} customers flagged ---")

print("\n--- High value customers (top decile) ---")
print(run(q7))

print("\n--- Overall average session duration ---")
q10_avg_session = "SELECT ROUND(AVG(session_minutes), 1) AS avg_session_minutes FROM login_activity;"
print(run(q10_avg_session))

print("\n--- Feature adoption rate (% of customers who have used each feature) ---")
q10_adoption = """
SELECT
    feature_name,
    COUNT(DISTINCT customer_id) AS customers_used,
    ROUND(100.0 * COUNT(DISTINCT customer_id) / (SELECT COUNT(*) FROM customers), 1) AS adoption_pct
FROM feature_usage
GROUP BY feature_name
ORDER BY adoption_pct DESC;
"""
print(run(q10_adoption))

conn.close()
print("\nDone.")