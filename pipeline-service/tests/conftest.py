import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from database import get_db
from main import app


class MockRow:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def __iter__(self):
        return iter(self._data.items())

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


def make_mock_db(initial_data=None):
    db = MagicMock(spec=Session)
    rows = list(initial_data) if initial_data else []

    def execute_side_effect(stmt, params=None):
        sql = str(stmt)
        if "COUNT" in sql:
            return MockMapping([{"count": len(rows)}])
        if params and "id" in params:
            matched = [r for r in rows if r["customer_id"] == params["id"]]
            return MockMapping(matched)
        if "LIMIT" in sql:
            offset = params.get("offset", 0)
            limit = params.get("limit", 10)
            return MockMapping(rows[offset:offset + limit])
        return MockMapping(rows)

    db.execute.side_effect = execute_side_effect
    return db


def override_get_db():
    db = MagicMock(spec=Session)
    yield db


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
