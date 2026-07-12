from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from services.ingestion import run_ingestion

app = FastAPI(title="Customer Data Pipeline")


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
    total = db.query(text("COUNT(*)")).select_from(text("customers")).scalar()
    rows = db.execute(
        text("SELECT * FROM customers ORDER BY customer_id LIMIT :limit OFFSET :offset"),
        {"limit": limit, "offset": offset},
    ).mappings().all()

    data = [dict(row) for row in rows]
    for c in data:
        if c.get("date_of_birth"):
            c["date_of_birth"] = str(c["date_of_birth"])
        if c.get("account_balance"):
            c["account_balance"] = float(c["account_balance"])
        if c.get("created_at"):
            c["created_at"] = str(c["created_at"])

    return {"data": data, "total": total, "page": page, "limit": limit}


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT * FROM customers WHERE customer_id = :id"),
        {"id": customer_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    c = dict(row)
    if c.get("date_of_birth"):
        c["date_of_birth"] = str(c["date_of_birth"])
    if c.get("account_balance"):
        c["account_balance"] = float(c["account_balance"])
    if c.get("created_at"):
        c["created_at"] = str(c["created_at"])

    return c
