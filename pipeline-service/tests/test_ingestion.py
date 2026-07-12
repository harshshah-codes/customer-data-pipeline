import pytest
from unittest.mock import patch, MagicMock, call
from datetime import date, datetime, timezone
from decimal import Decimal


MOCK_RESPONSE_PAGE1 = {
    "data": [
        {"customer_id": "C001", "first_name": "Alice", "last_name": "Johnson",
         "email": "alice@email.com", "phone": "555-0101",
         "address": "123 Maple St", "date_of_birth": "1990-05-14",
         "account_balance": 1250.75, "created_at": "2024-01-15T10:30:00Z"},
        {"customer_id": "C002", "first_name": "Bob", "last_name": "Smith",
         "email": "bob@email.com", "phone": "555-0102",
         "address": "456 Oak Ave", "date_of_birth": "1985-08-22",
         "account_balance": 3400.00, "created_at": "2024-01-16T11:00:00Z"},
    ],
    "total": 2,
    "page": 1,
    "limit": 100,
}

MOCK_RESPONSE_EMPTY = {"data": [], "total": 0, "page": 1, "limit": 100}


class TestFetchAllCustomers:
    @patch("services.ingestion.requests.get")
    def test_returns_all_customers_from_single_page(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: MOCK_RESPONSE_PAGE1)
        from services.ingestion import fetch_all_customers
        result = fetch_all_customers()
        assert len(result) == 2
        assert result[0]["customer_id"] == "C001"
        assert result[1]["customer_id"] == "C002"

    @patch("services.ingestion.requests.get")
    def test_handles_empty_response(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: MOCK_RESPONSE_EMPTY)
        from services.ingestion import fetch_all_customers
        result = fetch_all_customers()
        assert result == []

    @patch("services.ingestion.requests.get")
    def test_fetches_multiple_pages(self, mock_get):
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"data": [{"customer_id": "C001", "first_name": "A"}], "total": 150, "page": 1, "limit": 100}),
            MagicMock(status_code=200, json=lambda: {"data": [{"customer_id": "C002", "first_name": "B"}], "total": 150, "page": 2, "limit": 100}),
        ]
        from services.ingestion import fetch_all_customers
        result = fetch_all_customers()
        assert len(result) == 2
        assert mock_get.call_count == 2

    @patch("services.ingestion.requests.get")
    def test_uses_correct_url(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": [], "total": 0, "page": 1, "limit": 100})
        from services.ingestion import fetch_all_customers
        fetch_all_customers()
        args, kwargs = mock_get.call_args
        assert "mock-server" in args[0]

    @patch("services.ingestion.requests.get")
    def test_handles_flask_unavailable(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500)
        from services.ingestion import fetch_all_customers
        result = fetch_all_customers()
        assert result == []

    @patch("services.ingestion.requests.get")
    def test_paginates_correctly(self, mock_get):
        many_items = [{"customer_id": f"C{i:03d}"} for i in range(1, 251)]
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"data": many_items[:100], "total": 250, "page": 1, "limit": 100}),
            MagicMock(status_code=200, json=lambda: {"data": many_items[100:200], "total": 250, "page": 2, "limit": 100}),
            MagicMock(status_code=200, json=lambda: {"data": many_items[200:], "total": 250, "page": 3, "limit": 100}),
        ]
        from services.ingestion import fetch_all_customers
        result = fetch_all_customers()
        assert len(result) == 250


class TestParseCustomer:
    def test_returns_tuple(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        result = parse_customer(c)
        assert isinstance(result, tuple)
        assert len(result) == 9

    def test_parses_date_of_birth(self):
        from services.ingestion import parse_customer
        result = parse_customer({
            "customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
            "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"})
        assert result[6] == date(1990, 5, 14)

    def test_parses_created_at_with_z_suffix(self):
        from services.ingestion import parse_customer
        result = parse_customer({
            "customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
            "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"})
        assert result[8] == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_handles_none_dates(self):
        from services.ingestion import parse_customer
        result = parse_customer({
            "customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
            "date_of_birth": None, "created_at": None})
        assert result[6] is None
        assert result[8] is None

    def test_preserves_fields_in_correct_order(self):
        from services.ingestion import parse_customer
        result = parse_customer({
            "customer_id": "C010", "first_name": "Jack", "last_name": "Smith",
            "email": "jack@email.com", "phone": "555-0110",
            "address": "123 Street", "date_of_birth": "1990-05-14",
            "account_balance": 100.0, "created_at": "2024-01-15T10:30:00Z"})
        assert result[0] == "C010"
        assert result[1] == "Jack"
        assert result[2] == "Smith"
        assert result[3] == "jack@email.com"
        assert result[4] == "555-0110"
        assert result[5] == "123 Street"
        assert isinstance(result[6], date)
        assert isinstance(result[7], (int, float))
        assert isinstance(result[8], datetime)

    def test_handles_zero_balance(self):
        from services.ingestion import parse_customer
        result = parse_customer({
            "customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
            "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z",
            "account_balance": 0})
        assert result[7] == 0

    def test_handles_missing_optional_fields(self):
        from services.ingestion import parse_customer
        result = parse_customer({
            "customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
            "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"})
        assert result[4] is None
        assert result[5] is None
        assert result[7] is None

    def test_rejects_invalid_date(self):
        from services.ingestion import parse_customer
        with pytest.raises(ValueError):
            parse_customer({
                "customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
                "date_of_birth": "invalid", "created_at": "2024-01-15T10:30:00Z"})


class TestRunIngestion:
    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.psycopg2.connect")
    def test_ingests_customers(self, mock_connect, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "first_name": "Alice", "last_name": "Johnson",
             "email": "a@b.com", "phone": "555-0101", "address": "123 St",
             "date_of_birth": "1990-05-14", "account_balance": 100.0,
             "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        from services.ingestion import run_ingestion
        result = run_ingestion()

        assert result == 1
        assert mock_cur.execute.called

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.psycopg2.connect")
    def test_creates_table(self, mock_connect, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_cur = MagicMock()
        mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cur

        from services.ingestion import run_ingestion
        run_ingestion()

        create_calls = [c[0][0] for c in mock_cur.execute.call_args_list]
        assert any("CREATE TABLE" in str(s) for s in create_calls)

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.psycopg2.connect")
    def test_drops_table_before_creating(self, mock_connect, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_cur = MagicMock()
        mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cur

        from services.ingestion import run_ingestion
        run_ingestion()

        drop_calls = [c[0][0] for c in mock_cur.execute.call_args_list]
        assert any("DROP TABLE" in str(s) for s in drop_calls)
        assert str(drop_calls[0]) == "DROP TABLE IF EXISTS customers"
        assert "CREATE TABLE" in str(drop_calls[1])

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.psycopg2.connect")
    def test_uses_upsert(self, mock_connect, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_cur = MagicMock()
        mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cur

        from services.ingestion import run_ingestion
        run_ingestion()

        upsert_calls = [c[0][0] for c in mock_cur.executemany.call_args_list]
        assert any("ON CONFLICT" in str(s) for s in upsert_calls)

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.psycopg2.connect")
    def test_executemany_with_data(self, mock_connect, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"},
            {"customer_id": "C002", "first_name": "C", "last_name": "D", "email": "c@d.com",
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"},
        ]
        mock_cur = MagicMock()
        mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cur

        from services.ingestion import run_ingestion
        result = run_ingestion()

        assert result == 2
        assert mock_cur.executemany.called

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.psycopg2.connect")
    def test_zero_customers_skips_db(self, mock_connect, mock_fetch):
        mock_fetch.return_value = []
        from services.ingestion import run_ingestion
        result = run_ingestion()
        assert result == 0
        mock_connect.assert_not_called()

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.psycopg2.connect")
    def test_commits_transaction(self, mock_connect, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        from services.ingestion import run_ingestion
        run_ingestion()

        mock_conn.commit.assert_called_once()

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.psycopg2.connect")
    def test_closes_connection(self, mock_connect, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "first_name": "A", "last_name": "B", "email": "a@b.com",
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        from services.ingestion import run_ingestion
        run_ingestion()

        mock_conn.close.assert_called_once()
