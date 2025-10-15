import os
import uuid
import json
import time
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel
import httpx
import redis

# Config from env
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
POLICY_URL = os.getenv("POLICY_URL", "http://policy:7000/policy")
RETRIEVER_URL = os.getenv("RETRIEVER_URL", "http://retriever:7001/retrieve")
PROCESSOR_URL = os.getenv("PROCESSOR_URL", "http://processor:7002/process")
LOG_PATH = os.getenv("LOG_PATH", "/app/logs/audit.jsonl")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "5"))  # requests per minute

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

app = FastAPI(title="Gateway")

class ProcessRequest(BaseModel):
    request_id: str
    query: str

def write_audit(entry: Dict[str, Any]):
    line = json.dumps(entry)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

def get_trace_id():
    return str(uuid.uuid4())

def check_rate_limit(api_key: str):
    # rate limit per api_key: RATE_LIMIT requests per 60 sec
    key = f"rl:{api_key}"
    current = r.get(key)
    if current is None:
        # set with expiry 60s
        r.set(key, 1, ex=60)
        return True
    else:
        current = int(current)
        if current >= RATE_LIMIT:
            return False
        else:
            r.incr(key)
            return True

@app.post("/process-request")
async def process_request(req: ProcessRequest, x_api_key: str = Header(None)):
    trace_id = get_trace_id()
    request_id = req.request_id
    query = req.query
    audit = {"trace_id": trace_id, "request_id": request_id, "query": query, "status": None, "timestamp": int(time.time())}

    # 1) Validate API key
    if not x_api_key:
        audit["status"] = "missing_api_key"
        write_audit(audit)
        raise HTTPException(status_code=401, detail="Missing X-API-KEY header")
    # for demo accept any non-empty key; in real world check against DB
    # 2) Rate limiting
    if not check_rate_limit(x_api_key):
        audit["status"] = "rate_limited"
        write_audit(audit)
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded ({RATE_LIMIT}/min)")

    # 3) Idempotency: return cached response if present
    cache_key = f"resp:{request_id}"
    cached = r.get(cache_key)
    if cached:
        resp_json = json.loads(cached)
        audit["status"] = "ok_cached"
        write_audit({**audit, "status_detail": "returned cached response"})
        return resp_json

    # 4) Policy check (call policy service)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            policy_resp = await client.post(POLICY_URL, json={"request_id": request_id, "query": query, "trace_id": trace_id})
        except Exception as e:
            audit["status"] = "policy_error"
            write_audit({**audit, "error": str(e)})
            raise HTTPException(status_code=503, detail="Policy service unavailable")
        if policy_resp.status_code != 200:
            audit["status"] = "policy_denied"
            write_audit({**audit, "policy_response": policy_resp.text})
            raise HTTPException(status_code=403, detail="Policy denied the request")

    # 5) Call retriever
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            retriever_payload = {"request_id": request_id, "query": query, "trace_id": trace_id}
            rresp = await client.post(RETRIEVER_URL, json=retriever_payload)
            rresp.raise_for_status()
            retrieved = rresp.json()
    except Exception as e:
        audit["status"] = "retriever_error"
        write_audit({**audit, "error": str(e)})
        raise HTTPException(status_code=502, detail="Retriever service error")

    # 6) Call processor
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            proc_payload = {"request_id": request_id, "documents": retrieved.get("documents", []), "trace_id": trace_id}
            presp = await client.post(PROCESSOR_URL, json=proc_payload)
            presp.raise_for_status()
            processed = presp.json()
    except Exception as e:
        audit["status"] = "processor_error"
        write_audit({**audit, "error": str(e)})
        raise HTTPException(status_code=502, detail="Processor service error")

    # 7) Build final response
    response = {
        "request_id": request_id,
        "summary": processed.get("summary"),
        "label": processed.get("label"),
        "trace_id": trace_id
    }

    # 8) Cache response for idempotency (keep for 24 hours)
    r.set(cache_key, json.dumps(response), ex=24*3600)

    audit["status"] = "ok"
    write_audit(audit)
    return response

@app.get("/health")
def health():
    return {"status": "ok"}

