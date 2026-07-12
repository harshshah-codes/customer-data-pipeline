import os
import requests
import dlt
from dlt.destinations import postgres

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


def run_ingestion() -> int:
    customers = fetch_all_customers()
    if not customers:
        return 0

    pipeline = dlt.pipeline(
        pipeline_name="customer_ingestion",
        destination=postgres(credentials=os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/customer_db")),
        dataset_name="public",
    )

    pipeline.run(
        customers,
        table_name="customers",
        write_disposition="merge",
        primary_key="customer_id",
    )

    return len(customers)
