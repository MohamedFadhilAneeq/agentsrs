"""Minimal API wrapper around the pipeline, for the transparency frontend.

Run with:
    uvicorn backend.api:app --reload

Endpoints:
    GET  /                   -> serves frontend/index.html
    POST /analyze-single     -> single requirement, returns full trace + report
    POST /analyze-traced     -> SRS file upload, returns per-req traces + report
    POST /analyze            -> SRS file upload (original, no trace) -- kept for compat
    GET  /health             -> {"status": "ok"}
"""

import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.main import run_pipeline, run_single, run_pipeline_traced

app = FastAPI(title="AgentSRS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SingleRequest(BaseModel):
    requirement: str
    description: str | None = None


# Synchronous handlers so FastAPI runs them in the thread pool
# (they call time.sleep internally -- must not block the event loop)

@app.post("/analyze-single")
def analyze_single(req: SingleRequest):
    return run_single(req.requirement, req.description, provider="groq")


@app.post("/analyze-traced")
def analyze_traced(file: UploadFile):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="wb") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    return run_pipeline_traced(tmp_path, provider="groq")


@app.post("/analyze")
def analyze(file: UploadFile, provider: str = "groq"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="wb") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    return run_pipeline(tmp_path, provider=provider)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve the frontend -- mount AFTER all API routes so /analyze-* are not intercepted
_frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
