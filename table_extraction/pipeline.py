from .extractor import extract_tables
from .llm_schema import infer_schema
from .persistence import save_table

def process_pdf_for_tables(pdf_path: str):
    for df in extract_tables(pdf_path):
        schema = infer_schema(df)
        save_table(df, schema)