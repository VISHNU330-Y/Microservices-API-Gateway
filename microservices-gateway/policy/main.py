from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Policy Service")

class PolicyRequest(BaseModel):
    request_id: str
    query: str
    trace_id: str | None = None

@app.post("/policy")
async def policy(req: PolicyRequest):
    q = req.query or ""
    # Deny if query contains the word "forbidden" (case-insensitive)
    if "forbidden" in q.lower():
        # return 403 to gateway
        raise HTTPException(status_code=403, detail="Policy: query contains forbidden term")
    return {"allowed": True}

@app.get("/health")
def health():
    return {"status": "ok"}
 
