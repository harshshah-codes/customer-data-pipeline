#!/bin/bash
set -e

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

echo -e "\n[10] Flask Unit Tests" >> $OUTPUT
pip install pytest -q 2>/dev/null && cd mock-server && python -m pytest tests/ -v >> ../$OUTPUT 2>&1; cd ..

echo -e "\n\n[11] FastAPI Unit Tests" >> $OUTPUT
cd pipeline-service && python -m pytest tests/ -v >> ../$OUTPUT 2>&1; cd ..

echo -e "\n\n========================================" >> $OUTPUT
echo "ALL TESTS COMPLETE" >> $OUTPUT
echo "========================================" >> $OUTPUT

cat $OUTPUT
