from fastapi import FastAPI, UploadFile, File
from table_extraction.pipeline import process_pdf_for_tables

app = FastAPI()

@app.post("/upload-pdf")
async def upload(file: UploadFile = File(...)):
    path = f"/tmp/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    ok = process_pdf_for_tables(path)
    return {"success": ok}
