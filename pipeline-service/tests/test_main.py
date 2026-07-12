import pytest
from unittest.mock import patch, MagicMock
from main import app, serialize_row


class TestSerializeRow:
    def test_converts_date_to_string(self):
        from datetime import date
        row = {"date_of_birth": date(1990, 5, 14), "account_balance": 100.0, "created_at": None}
        result = serialize_row(row)
        assert result["date_of_birth"] == "1990-05-14"

    def test_converts_datetime_to_string(self):
        from datetime import datetime
        row = {"date_of_birth": None, "account_balance": 100.0, "created_at": datetime(2024, 1, 15, 10, 30, 0)}
        result = serialize_row(row)
        assert "2024-01-15" in result["created_at"]

    def test_converts_decimal_to_float(self):
        from decimal import Decimal
        row = {"date_of_birth": None, "account_balance": Decimal("1250.75"), "created_at": None}
        result = serialize_row(row)
        assert result["account_balance"] == 1250.75
        assert isinstance(result["account_balance"], float)

    def test_handles_none_balance(self):
        row = {"date_of_birth": None, "account_balance": None, "created_at": None}
        result = serialize_row(row)
        assert result["account_balance"] is None

    def test_handles_zero_balance(self):
        row = {"date_of_birth": None, "account_balance": 0, "created_at": None}
        result = serialize_row(row)
        assert result["account_balance"] == 0.0

    def test_handles_all_fields_none(self):
        row = {"date_of_birth": None, "account_balance": None, "created_at": None}
        result = serialize_row(row)
        assert result["date_of_birth"] is None
        assert result["account_balance"] is None
        assert result["created_at"] is None


class TestGetCustomers:
    def test_empty_database_returns_empty_list(self, client, empty_db):
        resp = client.get("/api/customers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["limit"] == 10

    def test_returns_paginated_results(self, client, seeded_db):
        resp = client.get("/api/customers?page=1&limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 3
        assert data["total"] == 10
        assert data["page"] == 1
        assert data["limit"] == 3

    def test_default_pagination(self, client, seeded_db):
        resp = client.get("/api/customers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["limit"] == 10
        assert data["total"] == 10

    def test_page_2_returns_remaining(self, client, seeded_db):
        resp = client.get("/api/customers?page=2&limit=5")
        data = resp.json()
        assert data["page"] == 2
        assert len(data["data"]) == 5

    def test_page_beyond_total_returns_empty(self, client, seeded_db):
        resp = client.get("/api/customers?page=100&limit=10")
        data = resp.json()
        assert data["data"] == []

    def test_response_has_correct_structure(self, client, seeded_db):
        resp = client.get("/api/customers?page=1&limit=2")
        data = resp.json()
        assert set(data.keys()) == {"data", "total", "page", "limit"}
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["limit"], int)

    def test_rejects_page_0(self, client):
        resp = client.get("/api/customers?page=0&limit=10")
        assert resp.status_code == 422

    def test_rejects_negative_page(self, client):
        resp = client.get("/api/customers?page=-1&limit=10")
        assert resp.status_code == 422

    def test_rejects_limit_0(self, client):
        resp = client.get("/api/customers?page=1&limit=0")
        assert resp.status_code == 422

    def test_rejects_negative_limit(self, client):
        resp = client.get("/api/customers?page=1&limit=-5")
        assert resp.status_code == 422

    def test_rejects_excessive_limit(self, client):
        resp = client.get("/api/customers?page=1&limit=200")
        assert resp.status_code == 422

    def test_orders_by_customer_id(self, client, seeded_db):
        resp = client.get("/api/customers?page=1&limit=10")
        ids = [c["customer_id"] for c in resp.json()["data"]]
        assert ids == sorted(ids)

    def test_types_are_serializable(self, client, seeded_db):
        resp = client.get("/api/customers?page=1&limit=1")
        c = resp.json()["data"][0]
        import json
        json.dumps(c)


class TestGetCustomer:
    def test_returns_customer_by_id(self, client, seeded_db):
        resp = client.get("/api/customers/C001")
        assert resp.status_code == 200
        assert resp.json()["customer_id"] == "C001"

    def test_returns_404_for_missing_id(self, client, seeded_db):
        resp = client.get("/api/customers/INVALID")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Customer not found"

    def test_returns_404_in_empty_db(self, client, empty_db):
        resp = client.get("/api/customers/C001")
        assert resp.status_code == 404

    def test_returns_404_for_special_chars(self, client, seeded_db):
        resp = client.get("/api/customers/!@#$%")
        assert resp.status_code == 404

    def test_case_sensitive(self, client, seeded_db):
        resp = client.get("/api/customers/c001")
        assert resp.status_code == 404


class TestIngest:
    @patch("main.run_ingestion", return_value=21)
    def test_ingest_returns_success_with_count(self, mock_ingest, client):
        resp = client.post("/api/ingest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["records_processed"] == 21

    @patch("main.run_ingestion", return_value=0)
    def test_ingest_with_zero_records(self, mock_ingest, client):
        resp = client.post("/api/ingest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["records_processed"] == 0

    @patch("main.run_ingestion", return_value=21)
    def test_ingest_is_idempotent(self, mock_ingest, client):
        resp1 = client.post("/api/ingest")
        resp2 = client.post("/api/ingest")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()

    @patch("main.run_ingestion", side_effect=Exception("DB connection failed"))
    def test_ingest_handles_database_error(self, mock_ingest, client):
        resp = client.post("/api/ingest")
        assert resp.status_code == 500
        assert "DB connection failed" in resp.json()["detail"]

    @patch("main.run_ingestion", side_effect=Exception("Flask unavailable"))
    def test_ingest_handles_flask_unavailable(self, mock_ingest, client):
        resp = client.post("/api/ingest")
        assert resp.status_code == 500
        assert "Flask unavailable" in resp.json()["detail"]

    @patch("main.run_ingestion", side_effect=Exception("timeout"))
    def test_ingest_handles_timeout(self, mock_ingest, client):
        resp = client.post("/api/ingest")
        assert resp.status_code == 500

    def test_ingest_only_accepts_post(self, client):
        resp = client.get("/api/ingest")
        assert resp.status_code == 405
        resp = client.put("/api/ingest")
        assert resp.status_code == 405
        resp = client.delete("/api/ingest")
        assert resp.status_code == 405
