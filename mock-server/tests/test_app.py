import json
import pytest
from app import app


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_returns_status_healthy(self, client):
        resp = client.get("/api/health")
        assert resp.get_json() == {"status": "healthy"}


class TestGetCustomers:
    def test_default_pagination(self, client):
        resp = client.get("/api/customers")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["page"] == 1
        assert data["limit"] == 10
        assert data["total"] == 21
        assert len(data["data"]) == 10

    def test_custom_page_and_limit(self, client):
        resp = client.get("/api/customers?page=2&limit=5")
        data = resp.get_json()
        assert data["page"] == 2
        assert data["limit"] == 5
        assert len(data["data"]) == 5
        assert data["data"][0]["customer_id"] == "C006"

    def test_last_page_returns_remaining(self, client):
        resp = client.get("/api/customers?page=3&limit=10")
        data = resp.get_json()
        assert len(data["data"]) == 1
        assert data["data"][0]["customer_id"] == "C021"

    def test_page_beyond_total_returns_empty(self, client):
        resp = client.get("/api/customers?page=100&limit=10")
        data = resp.get_json()
        assert data["data"] == []

    def test_page_0_is_clamped_to_1(self, client):
        resp = client.get("/api/customers?page=0&limit=5")
        data = resp.get_json()
        assert data["page"] == 1
        assert len(data["data"]) == 5

    def test_negative_page_is_clamped(self, client):
        resp = client.get("/api/customers?page=-5&limit=5")
        data = resp.get_json()
        assert data["page"] == 1
        assert len(data["data"]) == 5

    def test_negative_limit_is_clamped(self, client):
        resp = client.get("/api/customers?page=1&limit=-5")
        data = resp.get_json()
        assert data["limit"] == 10
        assert len(data["data"]) == 10

    def test_response_structure(self, client):
        resp = client.get("/api/customers?page=1&limit=2")
        data = resp.get_json()
        assert set(data.keys()) == {"data", "total", "page", "limit"}
        customer_keys = {
            "customer_id", "first_name", "last_name", "email",
            "phone", "address", "date_of_birth", "account_balance",
            "created_at",
        }
        assert set(data["data"][0].keys()) == customer_keys


class TestGetCustomer:
    def test_returns_customer_by_id(self, client):
        resp = client.get("/api/customers/C005")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["customer_id"] == "C005"
        assert data["first_name"] == "Eve"
        assert data["last_name"] == "Brown"

    def test_returns_404_for_missing_id(self, client):
        resp = client.get("/api/customers/INVALID")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Customer not found"

    def test_returns_404_for_empty_id(self, client):
        resp = client.get("/api/customers/")
        assert resp.status_code == 404

    def test_all_customers_have_unique_ids(self, client):
        resp = client.get("/api/customers?limit=100")
        ids = [c["customer_id"] for c in resp.get_json()["data"]]
        assert len(ids) == len(set(ids))
