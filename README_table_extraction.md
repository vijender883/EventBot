# Table‑Extraction → LLM → SQLite Pipeline

A **FastAPI** backend that:

1. Accepts a PDF upload.
2. Extracts every table (Camelot + pdfplumber fallback).
3. Sends a CSV sample to **Gemini 1.5‑pro** to infer JSON schema.
4. Creates/extends a SQLite table.
5. Stores rows + schema metadata.

---

\## 1  Project Layout

```
Chatbot_Pinecone_flask_backend/
├─ main.py                    # FastAPI entry‑point
├─ table_extraction/
│  ├─ __init__.py
│  ├─ extractor.py            # Camelot/pdfplumber logic
│  ├─ llm_schema.py           # Gemini prompt + validation
│  ├─ schema_models.py        # Pydantic models
│  ├─ persistence.py          # SQLAlchemy save logic
│  └─ pipeline.py             # orchestration
├─ uploads/                   # temp PDF storage
├─ show_db_url.py
├─ tables.db                  # SQLite file (auto‑created)
├─ .env                       # GOOGLE_API_KEY, DATABASE_URL, MODEL_ID
└─ requirements.txt
```

---

\## 2  Quick Start

```bash
# clone
$ git clone <repo_url>
$ cd Chatbot_Pinecone_flask_backend

# venv + deps
$ python -m venv venv && source venv/bin/activate      # Win: venv\Scripts\activate
$ pip install -r requirements.txt
$ python show_db_url.py                                # run this code to get DATABASE_URL

# .env example
GOOGLE_API_KEY=AIza...                           # from AI Studio
DATABASE_URL=sqlite:///./tables.db
MODEL_ID=gemini-1.5-pro-latest
```

---

\## 3  Run the server

```bash
$ uvicorn main:app --reload
# browse Swagger
> http://127.0.0.1:8000/docs
```

Upload any PDF containing tables → `{"success": true}`.

---

\## 4  Inspect SQLite results

\### CLI

```bash
$ sqlite3 tables.db ".tables"
$ sqlite3 tables.db "SELECT * FROM extracted_table_meta;"
```

\### VS Code GUI

1. Install extension **“SQLite Viewer”** by Florian Soare (marketplace id: floriansoare.sqlite‑viewer).
2. Press **⌥/Alt + Shift + S** or open the sidebar **SQLITE VIEWER**.
3. Click **“Add database”** → navigate to `tables.db`.
4. Expand tables → right‑click → **“Show Table”** to view rows.

---

\## 5  Key Files

| File             | What it does                                                                             |
| ---------------- | ---------------------------------------------------------------------------------------- |
| `extractor.py`   | Camelot lattice + pdfplumber stream fallback; returns `pd.DataFrame` list.               |
| `llm_schema.py`  | Sends cleaned CSV to Gemini, forces unique column names, validates with Pydantic.        |
| `persistence.py` | Adds any missing columns, inserts rows, upserts JSON schema into `extracted_table_meta`. |
| `pipeline.py`    | Glue code: extract → infer → save.                                                       |
| `main.py`        | FastAPI route `POST /upload` handles file I/O + calls pipeline.                          |

---

\## 6  Testing Locally

```bash
# single smoke‑test
$ python table_extraction/test_extract.py uploads/sample.pdf

# pytest suite (mocks Gemini)
$ pytest -q
```

---

\## 7  Troubleshooting Snippets

| Issue                     | Fix                                                                      |
| ------------------------- | ------------------------------------------------------------------------ |
| `DefaultCredentialsError` | Key missing → ensure `.env` loaded **before** imports (`load_dotenv()`). |
| gRPC 503 / IPv6           | `genai.configure(..., transport="rest")`.                                |
| `DuplicateColumnError`    | Pipeline pads/renames cols; ensure you pulled latest `persistence.py`.   |
| Table empty               | Confirm correct `tables.db` path printed on startup.                     |

---

\## 8  Swap SQLite for Postgres in production (`DATABASE_URL=postgresql://user:pw@host/db`).

