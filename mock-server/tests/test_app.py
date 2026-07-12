import json
import pytest
from app import app


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


@pytest.fixture
def sample_ids():
    return [f"C{i:03d}" for i in range(1, 22)]


class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_returns_status_healthy(self, client):
        resp = client.get("/api/health")
        assert resp.get_json() == {"status": "healthy"}

    def test_accepts_only_get(self, client):
        resp = client.post("/api/health")
        assert resp.status_code == 405


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

    def test_first_page_edge(self, client):
        resp = client.get("/api/customers?page=1&limit=1")
        data = resp.get_json()
        assert len(data["data"]) == 1
        assert data["data"][0]["customer_id"] == "C001"

    def test_last_page_returns_remaining(self, client):
        resp = client.get("/api/customers?page=3&limit=10")
        data = resp.get_json()
        assert len(data["data"]) == 1
        assert data["data"][0]["customer_id"] == "C021"

    def test_page_beyond_total_returns_empty_list(self, client):
        resp = client.get("/api/customers?page=100&limit=10")
        data = resp.get_json()
        assert data["data"] == []

    def test_page_0_clamps_to_1(self, client):
        resp = client.get("/api/customers?page=0&limit=5")
        data = resp.get_json()
        assert data["page"] == 1
        assert len(data["data"]) == 5

    def test_negative_page_clamps_to_1(self, client):
        resp = client.get("/api/customers?page=-3&limit=5")
        data = resp.get_json()
        assert data["page"] == 1
        assert len(data["data"]) == 5

    def test_limit_0_clamps_to_default(self, client):
        resp = client.get("/api/customers?page=1&limit=0")
        data = resp.get_json()
        assert data["limit"] == 10
        assert len(data["data"]) == 10

    def test_negative_limit_clamps_to_default(self, client):
        resp = client.get("/api/customers?page=1&limit=-1")
        data = resp.get_json()
        assert data["limit"] == 10

    def test_string_params_default_gracefully(self, client):
        resp = client.get("/api/customers?page=abc&limit=def")
        data = resp.get_json()
        assert data["page"] == 1
        assert data["limit"] == 10

    def test_very_large_limit_returns_all(self, client):
        resp = client.get("/api/customers?page=1&limit=1000")
        data = resp.get_json()
        assert len(data["data"]) == 21

    def test_all_records_returned_across_pages(self, client):
        all_records = []
        for page in range(1, 4):
            resp = client.get(f"/api/customers?page={page}&limit=10")
            all_records.extend(resp.get_json()["data"])
        assert len(all_records) == 21

    def test_response_has_correct_structure(self, client):
        resp = client.get("/api/customers?page=1&limit=2")
        data = resp.get_json()
        assert set(data.keys()) == {"data", "total", "page", "limit"}
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["limit"], int)

    def test_customer_fields_are_present(self, client):
        resp = client.get("/api/customers?page=1&limit=1")
        customer = resp.get_json()["data"][0]
        expected_keys = {
            "customer_id", "first_name", "last_name", "email",
            "phone", "address", "date_of_birth", "account_balance",
            "created_at",
        }
        assert set(customer.keys()) == expected_keys

    def test_customer_field_types(self, client):
        resp = client.get("/api/customers?page=1&limit=1")
        c = resp.get_json()["data"][0]
        assert isinstance(c["customer_id"], str)
        assert isinstance(c["first_name"], str)
        assert isinstance(c["last_name"], str)
        assert isinstance(c["email"], str)
        assert isinstance(c["phone"], str)
        assert isinstance(c["address"], str)
        assert isinstance(c["date_of_birth"], str)
        assert isinstance(c["account_balance"], (int, float))
        assert isinstance(c["created_at"], str)

    def test_all_customer_ids_are_unique(self, client):
        resp = client.get("/api/customers?limit=100")
        ids = [c["customer_id"] for c in resp.get_json()["data"]]
        assert len(ids) == len(set(ids))

    def test_account_balance_is_numeric(self, client):
        resp = client.get("/api/customers?limit=100")
        for c in resp.get_json()["data"]:
            assert isinstance(c["account_balance"], (int, float))
            assert c["account_balance"] >= 0

    def test_emails_contain_at_symbol(self, client):
        resp = client.get("/api/customers?limit=100")
        for c in resp.get_json()["data"]:
            assert "@" in c["email"]


class TestGetCustomer:
    def test_returns_customer_by_first_id(self, client):
        resp = client.get("/api/customers/C001")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["customer_id"] == "C001"
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Johnson"
        assert data["email"] == "alice.johnson@email.com"

    def test_returns_customer_by_last_id(self, client):
        resp = client.get("/api/customers/C021")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["customer_id"] == "C021"
        assert data["first_name"] == "Uma"

    def test_returns_customer_by_middle_id(self, client):
        resp = client.get("/api/customers/C010")
        data = resp.get_json()
        assert data["first_name"] == "Jack"
        assert data["last_name"] == "Jackson"

    def test_all_customer_fields_match_schema(self, client):
        resp = client.get("/api/customers/C001")
        data = resp.get_json()
        expected_keys = {
            "customer_id", "first_name", "last_name", "email",
            "phone", "address", "date_of_birth", "account_balance",
            "created_at",
        }
        assert set(data.keys()) == expected_keys

    def test_returns_404_for_nonexistent_id(self, client):
        resp = client.get("/api/customers/INVALID")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Customer not found"

    def test_returns_404_for_empty_id(self, client):
        resp = client.get("/api/customers/")
        assert resp.status_code == 404

    def test_returns_404_for_numeric_id(self, client):
        resp = client.get("/api/customers/99999")
        assert resp.status_code == 404

    def test_returns_404_for_special_chars(self, client):
        resp = client.get("/api/customers/!@#$%")
        assert resp.status_code == 404

    def test_case_sensitive_id(self, client):
        resp = client.get("/api/customers/c001")
        assert resp.status_code == 404

    def test_accepts_only_get(self, client):
        resp = client.post("/api/customers/C001")
        assert resp.status_code == 405
