from fastapi import FastAPI, UploadFile, File
import os, pathlib
from table_extraction.pipeline import process_pdf_for_tables   # adjust as needed
from pathlib import Path               #  ← add this line
app = FastAPI()

# ── define an absolute uploads folder ─────────────────────────
BASE_DIR      = pathlib.Path(__file__).resolve().parent        # folder containing main.py
UPLOADS_DIR   = BASE_DIR / "table_extraction" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)                 # create if missing
# ──────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    dest = Path("uploads") / file.filename
    dest.parent.mkdir(exist_ok=True)
    with dest.open("wb") as f:
        f.write(await file.read())

    try:
        ok = process_pdf_for_tables(str(dest))
        return {"success": ok}
    except Exception as e:
        return {"success": False, "error": str(e)}
