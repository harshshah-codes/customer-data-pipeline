from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, engine
from services.ingestion import run_ingestion

app = FastAPI(title="Customer Data Pipeline")

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


@app.on_event("startup")
def on_startup():
    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))


def serialize_row(row):
    c = dict(row)
    if "date_of_birth" in c and c["date_of_birth"] is not None:
        c["date_of_birth"] = str(c["date_of_birth"])
    if "account_balance" in c and c["account_balance"] is not None:
        c["account_balance"] = float(c["account_balance"])
    if "created_at" in c and c["created_at"] is not None:
        c["created_at"] = str(c["created_at"])
    return c


@app.post("/api/ingest")
def ingest():
    try:
        count = run_ingestion()
        return {"status": "success", "records_processed": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/customers")
def get_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    total = db.execute(text("SELECT COUNT(*) FROM customers")).scalar()
    rows = db.execute(
        text("SELECT * FROM customers ORDER BY customer_id LIMIT :limit OFFSET :offset"),
        {"limit": limit, "offset": offset},
    ).mappings().all()

    return {
        "data": [serialize_row(r) for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT * FROM customers WHERE customer_id = :id"),
        {"id": customer_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    return serialize_row(row)
