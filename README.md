# Customer Data Pipeline

A data pipeline with 3 Docker services: Flask Mock Server, FastAPI Ingestion Pipeline, and PostgreSQL.

## Architecture

```
Flask (JSON) → FastAPI (psycopg2 upsert) → PostgreSQL → FastAPI REST
```

The mock server generates 21 customer records. The pipeline fetches them via paginated HTTP, transforms fields (ISO dates→Python objects), and upserts into PostgreSQL using `INSERT ... ON CONFLICT DO UPDATE`. FastAPI serves the data back with pagination, sorting, and serialization.

## Services

| Service | Port | Description |
|---------|------|-------------|
| postgres | 5432 | PostgreSQL database |
| mock-server | 5000 | Flask REST API serving customer data |
| pipeline-service | 8000 | FastAPI data ingestion pipeline |

## Quick Start

```bash
# Start all services
docker compose up -d

# Check health
curl http://localhost:5000/api/health
```

## API Endpoints

### Flask Mock Server

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/customers?page=1&limit=10` | Paginated customer list |
| GET | `/api/customers/{id}` | Single customer |
| GET | `/api/health` | Health check |

### FastAPI Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ingest` | Ingest data from Flask into PostgreSQL |
| GET | `/api/customers?page=1&limit=10` | Paginated customers from database |
| GET | `/api/customers/{id}` | Single customer from database |

## Usage

```bash
# 1. Verify Flask is running
curl http://localhost:5000/api/customers?page=1&limit=5

# 2. Ingest data into PostgreSQL
curl -X POST http://localhost:8000/api/ingest

# 3. Query customers from FastAPI
curl http://localhost:8000/api/customers?page=1&limit=5

# 4. Get single customer
curl http://localhost:8000/api/customers/C001
```

## Running Tests

All tests run via the test script with Docker running:

```bash
./test_pipeline.sh
```

This runs:
- **Integration tests** (9): curl-based HTTP checks against live Flask/FastAPI endpoints
- **Unit tests** (95): pytest inside each container

| Suite | Tests | What it covers |
|-------|-------|----------------|
| Flask API | 31 | Health, pagination, 404, field types, edge cases |
| FastAPI pipeline | 31 | Serialization, pagination, 404, ingestion, validation |
| Ingestion logic | 22 | Multi-page fetch, parsing, upsert, transactions |
| Database & models | 11 | Connection, schema, constraints, column types |

## Project Structure

```
├── docker-compose.yml
├── test_pipeline.sh
├── README.md
├── mock-server/
│   ├── app.py
│   ├── data/customers.json
│   ├── Dockerfile
│   ├── requirements.txt
│   └── tests/
│       └── test_app.py
└── pipeline-service/
    ├── main.py
    ├── database.py
    ├── Dockerfile
    ├── requirements.txt
    ├── models/
    │   └── customer.py
    ├── services/
    │   └── ingestion.py
    └── tests/
        ├── conftest.py
        ├── test_main.py
        ├── test_ingestion.py
        └── test_database.py
```
