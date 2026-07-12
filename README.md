# Customer Data Pipeline

A data pipeline with 3 Docker services: Flask Mock Server, FastAPI Ingestion Pipeline, and PostgreSQL.

## Architecture

Flask (JSON) → FastAPI (Ingest via dlt) → PostgreSQL → API Response

## Services

| Service | Port | Description |
|---------|------|-------------|
| postgres | 5432 | PostgreSQL database |
| mock-server | 5000 | Flask REST API serving customer data |
| pipeline-service | 8000 | FastAPI data ingestion pipeline |

## Quick Start

```bash
# Start all services
docker-compose up -d

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

## Project Structure

```
├── docker-compose.yml
├── README.md
├── mock-server/
│   ├── app.py
│   ├── data/customers.json
│   ├── Dockerfile
│   └── requirements.txt
└── pipeline-service/
    ├── main.py
    ├── models/customer.py
    ├── services/ingestion.py
    ├── database.py
    ├── Dockerfile
    └── requirements.txt
```
