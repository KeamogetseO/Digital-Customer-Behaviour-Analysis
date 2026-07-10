# Digital Customer Behaviour Analysis: Bank Mobile App

## Project Overview
A South African bank launched a new mobile banking app. Six months in, app downloads are up but customer satisfaction is falling, many users register without becoming active, and some customers stop using the app after a few weeks.

This project acts as a behavioural data analyst consulting engagement: using SQL to investigate how customers actually use the app, which features drive engagement, where customers drop off, and which behaviours predict long-term usage.

## Tools Used
- **SQLite** : lightweight relational database, no server setup required
- **Python (sqlite3 + pandas)** : used to build the database and run/display SQL query results
- No external database server or GUI tool needed the entire project runs from two Python scripts

## Project Structure

(main.py): builds bank_app.db and generates sample data
(analysis.py): runs all 10 SQL tasks against bank_app.db
(bank_app.db): the SQLite database (created after running main.py)


## Database Schema
Four tables, matching a typical banking app's backend structure:

| Table | Description |
|---|---|
| customers| customer_id, age, gender, province, account_type, signup_date |
| login_activity | login_id, customer_id, login_date, session_minutes |
| transactions | transaction_id, customer_id, transaction_date, amount |
| feature_usage | usage_id, customer_id, feature_name, usage_date |

Sample data covers 80 customers, ~2,445 logins, ~1,066 transactions, and ~3,878 feature usage events between November 2025 and June 2026. Customer behaviour was deliberately varied (some customers barely engaged after signup, some went dormant partway through, most remained regular users) so the churn and dormancy analysis has realistic patterns to find.

## Analysis Tasks & SQL Concepts Covered

| # | Task | SQL Concepts |
|---|---|---|
| 1 | Active users per month | COUNT(), GROUP BY, date functions |
| 2 | Most popular features | COUNT(), GROUP BY, ORDER BY |
| 3 | Most engaged customers | SUM(), JOIN, GROUP BY |
| 4 | Engagement by province | JOIN, AVG(), GROUP BY |
| 5 | Customer journey (next feature used) | Window functions, LEAD() |
| 6 | Dormant customer identification | DATEDIFF-equivalent, HAVING, LEFT JOIN |
| 7 | High-value customer analysis | SUM(), NTILE(), window functions |
| 8 | Feature adoption timing | JOIN, CTE, date arithmetic |
| 9 | Churn behaviour comparison | CASE WHEN, aggregations, `CTE` |
| 10 | Executive dashboard dataset | Combines all of the above |

## Key Findings

- **Active users grew from 15 (Nov 2025) to a peak of 64 (Mar 2026)**, then began declining to 55 by June 2026,engagement growth is stalling, consistent with what the Head of Digital Banking flagged.
- **Transfer Money is the most-used feature** (1,097 uses), followed by Buy Airtime (831) and Pay Bills (749). Loan Applications is the least used (572), suggesting lower awareness or a more complex user flow for that feature.
- **24 of 80 customers (30%) are dormant**, defined as no login in the last 60 days. The longest-dormant customer hasn't logged in for 228 days.
- **Dormant customers behave very differently from active ones**: active customers average 39.9 logins and 17.6 transactions each, compared to just 8.8 logins and 3.3 transactions for dormant customers. Feature usage shows the same gap (63.6 vs 13.3 average uses). This is a clear early-warning signal: a drop in login frequency and feature usage precedes full churn.
- **Investments feature adoption is high** (93.8% of customers have used it at least once), and typically happens fast meaning an average of 18.8 days after signup, though a handful of customers take several months to discover it, pointing to inconsistent onboarding.
- **Gauteng generates the most transaction revenue** among provinces, though average session time is fairly consistent across all provinces (16.0–16.9 minutes), suggesting engagement itself isn't regionally driven, value generation is.

## Recommendations for the Bank

1. **Build a dormancy early-warning system** using the login/transaction/feature-usage drop-off pattern identified in Task 9, and trigger retention campaigns (push notifications, incentives) before customers pass the 60-day dormancy threshold, not after.
2. **Investigate the Loan Applications funnel** : its low usage relative to other features may indicate a UX or awareness problem worth a follow-up qualitative study.
3. **Standardise onboarding for feature discovery** : the wide spread in "days to adopt Investments" suggests some customers are simply not being shown premium features early enough.
4. **Prioritise retention over acquisition in the short term** :active user growth has plateaued since March, meaning the real lever for improving app health right now is deepening engagement, not driving more sign-ups.

## How to Run
1. Run main.py first : this creates bank_app.db and populates it with sample data.
2. Run analysis.py : this executes all 10 SQL tasks and prints the results.

