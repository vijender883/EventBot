import os, json, re, pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from .schema_models import TableSchema

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"), transport="rest")
MODEL_ID = os.getenv("MODEL_ID", "gemini-1.5-pro-latest")

SCHEMA_PROMPT = """
You are a database architect. Given a CSV sample, return ONLY valid JSON describing the schema. Do NOT explain or include code fences.

Rules:
- No blank, null or duplicate column names

Expected JSON format:
{{
  "table_name": "string",
  "columns": [{{"name":"string","type":"string","description":"string"}}],
  "primary_key": "string or null",
  "notes": "string"
}}

CSV Sample:
{csv}

Return ONLY the JSON.
"""

def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, df.columns.notna()]
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    seen = {}
    new_cols = []
    for i, col in enumerate(df.columns):
        base = str(col).strip() or f"col_{i}"
        cnt = seen.get(base, 0)
        new_name = base if cnt == 0 else f"{base}_{cnt}"
        seen[base] = cnt + 1
        new_cols.append(new_name)
    df.columns = new_cols
    return df

def _extract_json(text: str) -> dict:
    if text.startswith("```"):
        text = re.sub(r"```.*?\n|\n```", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("LLM returned no JSON")
    return json.loads(m.group())

def _fix_schema(schema: dict) -> dict:
    seen = {}
    for i, col in enumerate(schema["columns"]):
        name = str(col.get("name") or "").strip()
        base = name if name and name.lower() != "none" else f"col_{i}"
        cnt = seen.get(base, 0)
        new_name = base if cnt == 0 else f"{base}_{cnt}"
        seen[base] = cnt + 1
        col["name"] = new_name
        col["type"] = col.get("type") or "string"
        col["description"] = col.get("description") or ""
    schema["primary_key"] = schema.get("primary_key") or None
    return schema

def infer_schema(df: pd.DataFrame) -> dict:
    df = _clean_dataframe(df)
    prompt = SCHEMA_PROMPT.format(csv=df.to_csv(index=False))
    raw = genai.GenerativeModel(MODEL_ID).generate_content(prompt).text.strip()
    schema = _fix_schema(_extract_json(raw))
    TableSchema(**schema)
    df.columns = [c["name"] for c in schema["columns"]]
    return schema

