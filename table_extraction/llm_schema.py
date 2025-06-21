import pandas as pd
import google.generativeai as genai
import os, json
from schema_models import TableSchema

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SCHEMA_PROMPT = """You are a database architect. Given a table sample in CSV format, output a JSON structure that represents the schema.

CSV:
{csv}

Respond with a single-line JSON like:
{{
  "table_name": "snake_case_name",
  "columns": [
    {{"name": "column1", "type": "string", "description": "..." }},
    ...
  ],
  "primary_key": null,
  "notes": "Any observations or constraints"
}}"""

model = genai.GenerativeModel("gemini-pro")

def infer_schema(df: pd.DataFrame):
    csv_str = df.to_csv(index=False)
    prompt = SCHEMA_PROMPT.format(csv=csv_str)

    response = model.generate_content(prompt)
    content = response.text.strip()

    try:
        json_line = content.splitlines()[0] if "\n" in content else content
        return json.loads(json_line)
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {content}") from e
