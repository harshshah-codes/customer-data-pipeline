import os
from datetime import date, datetime
import requests
import dlt
from dlt.destinations import postgres
from sqlalchemy import text
from database import engine

FLASK_BASE_URL = os.getenv("FLASK_BASE_URL", "http://mock-server:5000")


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
    return {
        **c,
        "date_of_birth": date.fromisoformat(c["date_of_birth"]) if c.get("date_of_birth") else None,
        "created_at": datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")) if c.get("created_at") else None,
    }


def run_ingestion() -> int:
    customers = fetch_all_customers()
    if not customers:
        return 0

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS _dlt_pipeline_state CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS _dlt_loads CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS _dlt_version CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS customers CASCADE"))

    parsed = [parse_customer(c) for c in customers]

    pipeline = dlt.pipeline(
        pipeline_name="customer_ingestion",
        destination=postgres(credentials=os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/customer_db")),
        dataset_name="public",
    )

    pipeline.run(
        parsed,
        table_name="customers",
        write_disposition="merge",
        primary_key="customer_id",
    )

    return len(parsed)
