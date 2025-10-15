from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Processor")

class ProcessPayload(BaseModel):
    request_id: str
    documents: List[dict]
    trace_id: str | None = None

@app.post("/process")
async def process(payload: ProcessPayload):
    docs = payload.documents or []
    if not docs:
        raise HTTPException(status_code=400, detail="No documents to process")

    # Very simple summarization: concatenate first sentences and trim
    sentences = []
    for d in docs:
        text = d.get("text","")
        first_sentence = text.split(".")[0]
        if first_sentence:
            sentences.append(first_sentence.strip())
    summary = " ".join(sentences)
    if len(summary) > 300:
        summary = summary[:297] + "..."

    # Simple labeling: label based on keywords
    label = "general"
    summary_lower = summary.lower()
    if "vitamin" in summary_lower or "vitamin c" in summary_lower:
        label = "nutrition"
    elif "sweet" in summary_lower or "sugar" in summary_lower:
        label = "taste"
    elif "potassium" in summary_lower:
        label = "mineral"

    return {"request_id": payload.request_id, "summary": summary, "label": label, "trace_id": payload.trace_id}

@app.get("/health")
def health():
    return {"status": "ok"}

