import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from database import get_db
from main import app


class MockRow:
    def __init__(self, data):
        self._data = data
        for k, v in data.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __iter__(self):
        return iter(self._data.keys())

    def __contains__(self, key):
        return key in self._data


class MockMapping:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return [MockRow(r) for r in self._rows]

    def first(self):
        if self._rows:
            return MockRow(self._rows[0])
        return None

    def mappings(self):
        return self

    def scalar(self):
        if self._rows:
            return list(self._rows[0].values())[0]
        return 0


def make_mock_db(data=None):
    db = MagicMock(spec=Session)
    rows = list(data) if data else []

    def execute_side_effect(stmt, params=None):
        sql = str(stmt).lower()
        params = params or {}

        if "count(*)" in sql or "count(1)" in sql:
            return MockMapping([{"count": len(rows)}])

        if "where" in sql:
            matched = [r for r in rows if r.get("customer_id") == params.get("id", params.get("customer_id"))]
            return MockMapping(matched)

        if "limit" in sql:
            offset = int(params.get("offset", 0))
            limit_val = int(params.get("limit", 10))
            return MockMapping(rows[offset:offset + limit_val])

        return MockMapping(rows)

    db.execute.side_effect = execute_side_effect
    return db


def clear_dependency_overrides():
    app.dependency_overrides.clear()


@pytest.fixture
def empty_db():
    clear_dependency_overrides()
    db = make_mock_db([])
    app.dependency_overrides[get_db] = lambda: db
    yield db
    clear_dependency_overrides()


@pytest.fixture
def sample_data():
    return [
        {
            "customer_id": f"C{i:03d}",
            "first_name": "First",
            "last_name": f"Last{i}",
            "email": f"user{i}@email.com",
            "phone": f"555-{i:04d}",
            "address": f"{i} Main St",
            "date_of_birth": "1990-01-01",
            "account_balance": float(i * 100),
            "created_at": "2024-01-15 10:30:00",
        }
        for i in range(1, 11)
    ]


@pytest.fixture
def seeded_db(sample_data):
    clear_dependency_overrides()
    db = make_mock_db(sample_data)
    app.dependency_overrides[get_db] = lambda: db
    yield db
    clear_dependency_overrides()


@pytest.fixture
def client():
    clear_dependency_overrides()
    with TestClient(app) as c:
        yield c
    clear_dependency_overrides()
