# app/main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import json
import os
from typing import List, Any, Dict

from .ingest import Ingestor
from .agent import Agent

# FastAPI app
app = FastAPI(title="Autonomous QA Agent")

# Allow CORS for local dev (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = Path.cwd()
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Instantiate components
# Ingestor may construct chroma client and sentence-transformer; this will run on import/instantiation.
ingestor = Ingestor()
agent = Agent()


@app.get("/")
async def health():
    return {"status": "ok"}


@app.post("/upload/")
async def upload(files: List[UploadFile] = File(...)):
    """
    Save uploaded support documents / checkout.html into uploads/ directory.
    Returns list of saved file paths.
    """
    saved = []
    for f in files:
        out_path = UPLOAD_DIR / f.filename
        try:
            with out_path.open("wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            saved.append(str(out_path))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed saving {f.filename}: {e}")
    return {"saved": saved}


@app.post("/build_kb/")
async def build_kb():
    """
    Ingest all files currently present in uploads/ into the vector DB via Ingestor.
    """
    paths = [str(p) for p in UPLOAD_DIR.iterdir() if p.is_file()]
    if not paths:
        return {"status": "ok", "ingested_chunks": 0, "note": "no files found in uploads/"}
    # ingestor.ingest_files may return an int or a tuple depending on implementation; normalize to int
    n = ingestor.ingest_files(paths)
    try:
        # if returned tuple like (n,)
        if isinstance(n, (list, tuple)):
            ingested = int(n[0])
        else:
            ingested = int(n)
    except Exception:
        # fallback: try to coerce, otherwise return raw
        ingested = n
    return {"status": "ok", "ingested_chunks": ingested}


@app.post("/generate_testcases/")
async def generate_testcases(query: str = Form(...)):
    """
    Generate test cases based on the user's query. Returns the agent output as-is.
    The agent returns either:
      {"testcases": [ ... ]}   # successful structured output
    or {"raw": "<LLM output>", "note": "..."}  # parsing failed, raw shown for inspection
    """
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=400, detail="query form field is required.")
    result = agent.generate_test_cases(query)
    # result is expected to be a dict (see app/agent.Agent.generate_test_cases)
    return result


@app.post("/generate_selenium/")
async def generate_selenium(test_case: str = Form(...), html_file: UploadFile = File(...)):
    """
    Generate a Selenium (Python) script for the provided test_case and checkout.html file.
    - test_case: JSON string (Streamlit sends json.dumps(test_case) in form data)
    - html_file: uploaded checkout.html
    Returns: {"script": "<python code as string>"}
    """
    # Parse test_case JSON string into dict
    try:
        tc_obj: Dict[str, Any] = json.loads(test_case) if isinstance(test_case, str) else test_case
        if not isinstance(tc_obj, dict):
            raise ValueError("Parsed test_case is not a JSON object.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid test_case JSON: {e}")

    # Read uploaded html content
    try:
        raw_bytes = await html_file.read()
        html_text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read html_file: {e}")

    # Call agent to produce selenium script (string)
    try:
        script = agent.generate_selenium(tc_obj, html_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed to generate selenium script: {e}")

    # Return the script (may be raw text or code block)
    return {"script": script}
