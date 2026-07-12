import pytest
from unittest.mock import patch, MagicMock


class TestDatabaseConnection:
    def test_database_url_contains_postgres(self):
        import database
        assert "postgres" in str(database.engine.url)

    def test_engine_has_pool_pre_ping(self):
        import database
        assert database.engine.pool._pre_ping is True

    def test_session_local_is_bound_to_engine(self):
        import database
        assert database.SessionLocal.kw["bind"] == database.engine

    def test_get_db_returns_session_generator(self):
        import database
        gen = database.get_db()
        db = next(gen)
        assert db is not None
        gen.close()

    def test_base_is_declarative(self):
        import database
        from sqlalchemy.orm import DeclarativeBase
        assert hasattr(database.Base, "metadata")


class TestCustomerModel:
    def test_model_has_correct_table_name(self):
        from models.customer import Customer
        assert Customer.__tablename__ == "customers"

    def test_model_has_all_required_columns(self):
        from models.customer import Customer
        columns = Customer.__table__.columns
        expected = [
            "customer_id", "first_name", "last_name", "email",
            "phone", "address", "date_of_birth", "account_balance",
            "created_at",
        ]
        for col in expected:
            assert col in columns, f"Missing column: {col}"

    def test_customer_id_is_primary_key(self):
        from models.customer import Customer
        pk = Customer.__table__.primary_key
        assert len(pk.columns) == 1
        assert list(pk.columns)[0].name == "customer_id"

    def test_required_fields_not_null(self):
        from models.customer import Customer
        cols = Customer.__table__.columns
        assert not cols["customer_id"].nullable
        assert not cols["first_name"].nullable
        assert not cols["last_name"].nullable
        assert not cols["email"].nullable

    def test_optional_fields_nullable(self):
        from models.customer import Customer
        cols = Customer.__table__.columns
        assert cols["phone"].nullable
        assert cols["address"].nullable
        assert cols["date_of_birth"].nullable
        assert cols["account_balance"].nullable
        assert cols["created_at"].nullable

    def test_account_balance_precision(self):
        from models.customer import Customer
        col = Customer.__table__.columns["account_balance"]
        assert str(col.type) == "NUMERIC(15, 2)"
