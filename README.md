# Microservices API Gateway Assignment

## Overview

This project demonstrates a **3-service AI microservices architecture** behind an **API Gateway**. The system allows clients to send requests to retrieve, process, and summarize data, with **authentication, policy checks, rate limiting, caching, and logging** implemented.

**Architecture:**

* **API Gateway (Kong-based)**: Routes requests, enforces API key authentication, rate limiting (5 requests/min), calls Policy Service, and logs requests with `trace_id` and `request_id`.
* **Retriever Agent**: Fetches top 3 matching documents from a dataset.
* **Processor Agent**: Summarizes documents and adds a label.
* **Policy Service (stub)**: Blocks queries containing `"forbidden"`.

---

## Features

* API Key Authentication (`X-API-KEY`)
* Rate limiting (5 requests per minute)
* Policy enforcement (blocks forbidden queries)
* Request logging (`trace_id`, `request_id`, `status`, `timestamp`)
* Idempotent request handling (cached responses for repeated `request_id`)
* Dockerized microservices with `docker-compose`
* JSON logs in `logs/audit.jsonl` for traceability

---

## Endpoints

### 1. Gateway

* **POST /process-request**
  **Headers:**

  ```
  Content-Type: application/json
  X-API-KEY: <your-api-key>
  ```

  **Body Example:**

  ```json
  {
    "request_id": "req-123",
    "query": "vitamin C in apples"
  }
  ```

  **Response Example:**

  ```json
  {
    "request_id": "req-123",
    "summary": "Apples are red and sweet Elderberries are used in syrups and contain vitamin C Bananas are yellow and rich in potassium",
    "label": "nutrition",
    "trace_id": "e0e7f9f4-4f41-45e0-bae4-d6aa7b093655"
  }
  ```

### 2. Policy Service

* **POST /policy**
  Denies requests containing `"forbidden"` in the query.

### 3. Retriever Agent

* **POST /retrieve**
  Returns top 3 matching documents from the dataset.

### 4. Processor Agent

* **POST /process**
  Summarizes documents and labels the output.

---

## Setup Instructions

1. **Clone the repository**

```bash
git clone <your-repo-url>
cd microservices-gateway
```

2. **Start all services using Docker Compose**

```bash
docker compose up --build
```

3. **Test the API**

```bash
curl -s -X POST "http://localhost:8000/process-request" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: my-test-key" \
  -d "{\"request_id\":\"req-123\",\"query\":\"vitamin C in apples\"}"
```

---

## Logging

All requests are logged in **JSON Lines format**:
`logs/audit.jsonl`
Example:

```json
{
  "trace_id": "e0e7f9f4-4f41-45e0-bae4-d6aa7b093655",
  "request_id": "req-123",
  "query": "vitamin C in apples",
  "status": "ok",
  "timestamp": 1760506064
}
```

Repeated requests with the same `request_id` will show `status: ok_cached`.

---

## Notes

* Ensure Docker Desktop or Docker Engine is running.
* Test forbidden queries to confirm Policy Service enforcement.
* Rate limiting and caching are enforced per API key.

---

## Authors

**Vishnu Vardhan Reddy Yerasi** – Developer and Designer

