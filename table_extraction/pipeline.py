from .extractor import extract_tables
from .llm_schema import infer_schema
from .persistence import save_table
from .schema_models import TableSchema

def process_pdf_for_tables(pdf_path: str) -> bool:
    tables = extract_tables(pdf_path)
    for df in tables:
        schema = infer_schema(df)
        save_table(df, schema)
    return True   # ✅ explicitly return success
