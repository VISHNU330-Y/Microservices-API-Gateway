from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import heapq

app = FastAPI(title="Retriever")

# Simple in-memory dataset for demo
DATASET = [
    {"id": "d1", "text": "Apples are red and sweet. They contain vitamin C."},
    {"id": "d2", "text": "Bananas are yellow and rich in potassium."},
    {"id": "d3", "text": "Cherries have antioxidants and are small and red."},
    {"id": "d4", "text": "Dates are sweet fruits often used in deserts."},
    {"id": "d5", "text": "Elderberries are used in syrups and contain vitamin C."}
]

class RetrieveRequest(BaseModel):
    request_id: str
    query: str
    trace_id: str | None = None

@app.post("/retrieve")
async def retrieve(req: RetrieveRequest):
    q = req.query.lower()
    # Naive scoring: count word overlap
    scores = []
    q_words = set(q.split())
    for doc in DATASET:
        doc_words = set(doc["text"].lower().split())
        score = len(q_words & doc_words)
        scores.append((score, doc))
    # get top 3
    top = heapq.nlargest(3, scores, key=lambda x: x[0])
    results = [d for score, d in top if score>0]
    # If nothing matched, return first 3 as fallback
    if not results:
        results = [d for d in DATASET[:3]]
    return {"request_id": req.request_id, "documents": results, "trace_id": req.trace_id}

@app.get("/health")
def health():
    return {"status": "ok"}
 
