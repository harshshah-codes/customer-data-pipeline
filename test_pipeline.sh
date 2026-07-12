#!/bin/bash
OUTPUT="test_output.txt"
echo "========================================" > $OUTPUT
echo "CUSTOMER DATA PIPELINE - INTEGRATION TESTS" >> $OUTPUT
echo "========================================" >> $OUTPUT

echo -e "\n[1] Flask Health Check" >> $OUTPUT
curl -s http://localhost:5000/api/health | python3 -m json.tool >> $OUTPUT 2>&1

echo -e "\n\n[2] Flask Paginated Customers (page=1, limit=3)" >> $OUTPUT
curl -s "http://localhost:5000/api/customers?page=1&limit=3" | python3 -m json.tool >> $OUTPUT 2>&1

echo -e "\n\n[3] Flask Single Customer (C001)" >> $OUTPUT
curl -s http://localhost:5000/api/customers/C001 | python3 -m json.tool >> $OUTPUT 2>&1

echo -e "\n\n[4] Flask 404 (INVALID)" >> $OUTPUT
curl -s -o /tmp/flask_404.json -w "HTTP Status: %{http_code}\n" http://localhost:5000/api/customers/INVALID >> $OUTPUT 2>&1
python3 -m json.tool /tmp/flask_404.json >> $OUTPUT 2>&1

echo -e "\n\n[5] Ingest Data (POST /api/ingest)" >> $OUTPUT
curl -s -X POST http://localhost:8000/api/ingest | python3 -m json.tool >> $OUTPUT 2>&1

echo -e "\n\n[6] FastAPI Paginated Customers (page=1, limit=3)" >> $OUTPUT
curl -s "http://localhost:8000/api/customers?page=1&limit=3" | python3 -m json.tool >> $OUTPUT 2>&1

echo -e "\n\n[7] FastAPI Single Customer (C010)" >> $OUTPUT
curl -s http://localhost:8000/api/customers/C010 | python3 -m json.tool >> $OUTPUT 2>&1

echo -e "\n\n[8] FastAPI 404 (INVALID)" >> $OUTPUT
curl -s -o /tmp/fastapi_404.json -w "HTTP Status: %{http_code}\n" http://localhost:8000/api/customers/INVALID >> $OUTPUT 2>&1
python3 -m json.tool /tmp/fastapi_404.json >> $OUTPUT 2>&1

echo -e "\n\n[9] FastAPI Page 2 Test" >> $OUTPUT
curl -s "http://localhost:8000/api/customers?page=2&limit=5" | python3 -m json.tool >> $OUTPUT 2>&1

echo -e "\n\n========================================" >> $OUTPUT
echo "UNIT TESTS" >> $OUTPUT
echo "========================================" >> $OUTPUT

echo -e "\n[10] Flask Unit Tests (test_app.py)" >> $OUTPUT
docker exec mock-server pip install pytest -q 2>/dev/null
docker exec -w /app mock-server python -m pytest tests/ -v --tb=short 2>&1 >> $OUTPUT || true

echo -e "\n\n[11] FastAPI Unit Tests (test_main.py)" >> $OUTPUT
docker exec pipeline-service pip install pytest -q 2>/dev/null
docker exec -w /app pipeline-service python -m pytest tests/test_main.py -v --tb=short 2>&1 >> $OUTPUT || true

echo -e "\n\n[12] Ingestion Unit Tests (test_ingestion.py)" >> $OUTPUT
docker exec -w /app pipeline-service python -m pytest tests/test_ingestion.py -v --tb=short 2>&1 >> $OUTPUT || true

echo -e "\n\n[13] Database & Model Tests (test_database.py)" >> $OUTPUT
docker exec -w /app pipeline-service python -m pytest tests/test_database.py -v --tb=short 2>&1 >> $OUTPUT || true

echo -e "\n\n========================================" >> $OUTPUT
echo "TEST SUMMARY" >> $OUTPUT
echo "========================================" >> $OUTPUT

echo -e "\nIntegration Tests: [1]-[9] above" >> $OUTPUT
echo "Unit Tests: [10] Flask, [11] FastAPI, [12] Ingestion, [13] Database" >> $OUTPUT
echo "========================================" >> $OUTPUT
echo "ALL TESTS COMPLETE" >> $OUTPUT
echo "========================================" >> $OUTPUT

cat $OUTPUT
