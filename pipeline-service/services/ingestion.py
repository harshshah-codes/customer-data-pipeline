import os
from datetime import date, datetime
import psycopg2
import requests

FLASK_BASE_URL = os.getenv("FLASK_BASE_URL", "http://mock-server:5000")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    date_of_birth DATE,
    account_balance DECIMAL(15,2),
    created_at TIMESTAMP
)
"""

UPSERT_SQL = """
INSERT INTO customers (customer_id, first_name, last_name, email, phone, address, date_of_birth, account_balance, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (customer_id)
DO UPDATE SET
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    address = EXCLUDED.address,
    date_of_birth = EXCLUDED.date_of_birth,
    account_balance = EXCLUDED.account_balance,
    created_at = EXCLUDED.created_at
"""


def fetch_all_customers():
    all_customers = []
    page = 1
    limit = 100

    while True:
        resp = requests.get(
            f"{FLASK_BASE_URL}/api/customers",
            params={"page": page, "limit": limit},
            timeout=10,
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        all_customers.extend(data["data"])
        total_pages = (data["total"] + limit - 1) // limit
        if page >= total_pages:
            break
        page += 1

    return all_customers


def parse_customer(c):
    dob = None
    if c.get("date_of_birth"):
        dob = date.fromisoformat(c["date_of_birth"])
    created = None
    if c.get("created_at"):
        created = datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))
    return (
        c["customer_id"],
        c["first_name"],
        c["last_name"],
        c["email"],
        c.get("phone"),
        c.get("address"),
        dob,
        c.get("account_balance"),
        created,
    )


def run_ingestion() -> int:
    customers = fetch_all_customers()
    if not customers:
        return 0

    records = [parse_customer(c) for c in customers]
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/customer_db")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            cur.executemany(UPSERT_SQL, records)
        conn.commit()
    finally:
        conn.close()

    return len(records)
