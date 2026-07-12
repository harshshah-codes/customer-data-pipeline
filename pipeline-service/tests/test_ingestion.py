import pytest
from unittest.mock import patch, MagicMock, call
from datetime import date, datetime


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
        page1 = {
            "data": [{"customer_id": "C001", "first_name": "A"}],
            "total": 2,
            "page": 1,
            "limit": 1,
        }
        page2 = {
            "data": [{"customer_id": "C002", "first_name": "B"}],
            "total": 2,
            "page": 2,
            "limit": 1,
        }
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: page1),
            MagicMock(status_code=200, json=lambda: page2),
        ]
        from services.ingestion import fetch_all_customers
        result = fetch_all_customers()
        assert len(result) == 2
        assert mock_get.call_count == 2

    @patch("services.ingestion.requests.get")
    def test_uses_correct_url(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [], "total": 0, "page": 1, "limit": 100},
        )
        from services.ingestion import fetch_all_customers
        fetch_all_customers()
        args, kwargs = mock_get.call_args
        assert "mock-server" in args[0]
        assert "page=1" in kwargs["params"] or "page=1" in args[0]

    @patch("services.ingestion.requests.get")
    def test_handles_flask_unavailable(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500)
        from services.ingestion import fetch_all_customers
        result = fetch_all_customers()
        assert result == []

    @patch("services.ingestion.requests.get")
    def test_handles_connection_timeout(self, mock_get):
        mock_get.side_effect = Exception("Connection timeout")
        from services.ingestion import fetch_all_customers
        with pytest.raises(Exception):
            fetch_all_customers()

    @patch("services.ingestion.requests.get")
    def test_paginates_correctly(self, mock_get):
        many_items = [
            {"customer_id": f"C{i:03d}"} for i in range(1, 51)
        ]
        page1 = {"data": many_items[:20], "total": 50, "page": 1, "limit": 20}
        page2 = {"data": many_items[20:40], "total": 50, "page": 2, "limit": 20}
        page3 = {"data": many_items[40:], "total": 50, "page": 3, "limit": 20}
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: page1),
            MagicMock(status_code=200, json=lambda: page2),
            MagicMock(status_code=200, json=lambda: page3),
        ]
        from services.ingestion import fetch_all_customers
        result = fetch_all_customers()
        assert len(result) == 50


class TestParseCustomer:
    def test_parses_date_of_birth(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        result = parse_customer(c)
        assert result["date_of_birth"] == date(1990, 5, 14)

    def test_parses_created_at_with_z_suffix(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        result = parse_customer(c)
        assert result["created_at"] == datetime(2024, 1, 15, 10, 30, 0)

    def test_parses_created_at_with_offset(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00+00:00"}
        result = parse_customer(c)
        assert result["created_at"] is not None

    def test_handles_none_date_of_birth(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "date_of_birth": None, "created_at": None}
        result = parse_customer(c)
        assert result["date_of_birth"] is None
        assert result["created_at"] is None

    def test_handles_missing_dates(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001"}
        result = parse_customer(c)
        assert result.get("date_of_birth") is None
        assert result.get("created_at") is None

    def test_preserves_other_fields(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "first_name": "Alice", "account_balance": 100.0,
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        result = parse_customer(c)
        assert result["customer_id"] == "C001"
        assert result["first_name"] == "Alice"
        assert result["account_balance"] == 100.0

    def test_account_balance_stays_float(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "account_balance": 1250.75,
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        result = parse_customer(c)
        assert isinstance(result["account_balance"], float)

    def test_handles_zero_balance(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "account_balance": 0,
             "date_of_birth": "1990-05-14", "created_at": "2024-01-15T10:30:00Z"}
        result = parse_customer(c)
        assert result["account_balance"] == 0

    def test_leap_year_date(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "date_of_birth": "2000-02-29", "created_at": "2024-01-15T10:30:00Z"}
        result = parse_customer(c)
        assert result["date_of_birth"] == date(2000, 2, 29)

    def test_rejects_invalid_date(self):
        from services.ingestion import parse_customer
        c = {"customer_id": "C001", "date_of_birth": "not-a-date", "created_at": "2024-01-15T10:30:00Z"}
        with pytest.raises(ValueError):
            parse_customer(c)


class TestRunIngestion:
    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.dlt.pipeline")
    @patch("services.ingestion.engine")
    def test_run_ingestion_success(self, mock_engine, mock_pipeline, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "first_name": "Alice", "last_name": "Johnson",
             "email": "alice@email.com", "phone": "555-0101",
             "address": "123 Maple St", "date_of_birth": "1990-05-14",
             "account_balance": 1250.75, "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        from services.ingestion import run_ingestion
        result = run_ingestion()

        assert result == 1
        mock_pipeline_instance.run.assert_called_once()

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.dlt.pipeline")
    @patch("services.ingestion.engine")
    def test_run_ingestion_zero_customers(self, mock_engine, mock_pipeline, mock_fetch):
        mock_fetch.return_value = []
        from services.ingestion import run_ingestion
        result = run_ingestion()
        assert result == 0
        mock_pipeline.assert_not_called()

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.dlt.pipeline")
    @patch("services.ingestion.engine")
    def test_run_ingestion_passes_parsed_data(self, mock_engine, mock_pipeline, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "date_of_birth": "1990-05-14",
             "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        from services.ingestion import run_ingestion
        run_ingestion()

        args, kwargs = mock_pipeline_instance.run.call_args
        parsed_data = args[0]
        assert isinstance(parsed_data[0]["date_of_birth"], date)
        assert isinstance(parsed_data[0]["created_at"], datetime)

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.dlt.pipeline")
    @patch("services.ingestion.engine")
    def test_run_ingestion_merge_disposition(self, mock_engine, mock_pipeline, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "date_of_birth": "1990-05-14",
             "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        from services.ingestion import run_ingestion
        run_ingestion()

        _, kwargs = mock_pipeline_instance.run.call_args
        assert kwargs["write_disposition"] == "merge"
        assert kwargs["primary_key"] == "customer_id"

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.dlt.pipeline")
    @patch("services.ingestion.engine")
    def test_run_ingestion_cleans_tables(self, mock_engine, mock_pipeline, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "date_of_birth": "1990-05-14",
             "created_at": "2024-01-15T10:30:00Z"}
        ]
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        from services.ingestion import run_ingestion
        run_ingestion()

        drop_calls = [c[0][0] for c in mock_conn.execute.call_args_list]
        sqls = [str(c) for c in drop_calls]
        assert any("DROP TABLE IF EXISTS _dlt_pipeline_state" in s for s in sqls)
        assert any("DROP TABLE IF EXISTS customers" in s for s in sqls)

    @patch("services.ingestion.fetch_all_customers")
    @patch("services.ingestion.dlt.pipeline")
    @patch("services.ingestion.engine")
    def test_run_ingestion_dataset_name(self, mock_engine, mock_pipeline, mock_fetch):
        mock_fetch.return_value = [
            {"customer_id": "C001", "date_of_birth": "1990-05-14",
             "created_at": "2024-01-15T10:30:00Z"}
        ]
        from services.ingestion import run_ingestion
        run_ingestion()
        kwargs = mock_pipeline.call_args.kwargs
        assert kwargs.get("dataset_name") == "public"
