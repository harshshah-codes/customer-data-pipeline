import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from main import app


SAMPLE_CUSTOMER = {
    "customer_id": "C001",
    "first_name": "Alice",
    "last_name": "Johnson",
    "email": "alice@email.com",
    "phone": "555-0101",
    "address": "123 Maple St",
    "date_of_birth": "1990-05-14",
    "account_balance": 1250.75,
    "created_at": "2024-01-15 10:30:00",
}

SAMPLE_CUSTOMERS = [
    {**SAMPLE_CUSTOMER, "customer_id": f"C{i:03d}"}
    for i in range(1, 11)
]


@pytest.fixture
def mock_db():
    """Inject a mock db session that returns sample data."""
    from conftest import make_mock_db
    db = make_mock_db(SAMPLE_CUSTOMERS)
    app.dependency_overrides.clear()

    def override():
        yield db

    from database import get_db
    app.dependency_overrides[get_db] = override
    yield db
    app.dependency_overrides.clear()


class TestGetCustomers:
    def test_returns_paginated_results(self, client, mock_db):
        resp = client.get("/api/customers?page=1&limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["limit"] == 3
        assert data["total"] == 10
        assert len(data["data"]) == 3

    def test_default_pagination(self, client, mock_db):
        resp = client.get("/api/customers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["limit"] == 10
        assert data["total"] == 10

    def test_page_2_returns_correct_slice(self, client, mock_db):
        resp = client.get("/api/customers?page=2&limit=5")
        data = resp.json()
        assert data["page"] == 2
        assert len(data["data"]) == 5
        assert data["data"][0]["customer_id"] == "C006"

    def test_empty_result_when_no_data(self, client):
        from conftest import make_mock_db
        db = make_mock_db([])

        def override():
            yield db

        from database import get_db
        app.dependency_overrides[get_db] = override

        resp = client.get("/api/customers?page=1&limit=5")
        data = resp.json()
        assert data["total"] == 0
        assert data["data"] == []

        app.dependency_overrides.clear()

    def test_serializes_types_correctly(self, client, mock_db):
        resp = client.get("/api/customers?page=1&limit=1")
        data = resp.json()
        c = data["data"][0]
        assert isinstance(c["account_balance"], float)
        assert isinstance(c["date_of_birth"], str)
        assert isinstance(c["created_at"], str)

    def test_rejects_invalid_page(self, client):
        resp = client.get("/api/customers?page=0&limit=10")
        assert resp.status_code == 422

    def test_rejects_excessive_limit(self, client):
        resp = client.get("/api/customers?page=1&limit=200")
        assert resp.status_code == 422


class TestGetCustomer:
    def test_returns_customer_by_id(self, client, mock_db):
        resp = client.get("/api/customers/C001")
        assert resp.status_code == 200
        assert resp.json()["customer_id"] == "C001"
        assert resp.json()["first_name"] == "Alice"

    def test_returns_404_for_missing(self, client, mock_db):
        resp = client.get("/api/customers/INVALID")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Customer not found"


class TestIngest:
    @patch("main.run_ingestion", return_value=21)
    def test_ingest_returns_success(self, mock_ingest, client):
        resp = client.post("/api/ingest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["records_processed"] == 21

    @patch("main.run_ingestion", side_effect=Exception("DB error"))
    def test_ingest_handles_errors(self, mock_ingest, client):
        resp = client.post("/api/ingest")
        assert resp.status_code == 500
        assert "DB error" in resp.json()["detail"]
