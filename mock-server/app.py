import json
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "customers.json")

with open(DATA_PATH, "r") as f:
    customers = json.load(f)

customers_index = {c["customer_id"]: c for c in customers}


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/api/customers", methods=["GET"])
def get_customers():
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    start = (page - 1) * limit
    end = start + limit
    data = customers[start:end]
    return jsonify({
        "data": data,
        "total": len(customers),
        "page": page,
        "limit": limit
    })


@app.route("/api/customers/<customer_id>", methods=["GET"])
def get_customer(customer_id):
    customer = customers_index.get(customer_id)
    if customer is None:
        return jsonify({"error": "Customer not found"}), 404
    return jsonify(customer)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
