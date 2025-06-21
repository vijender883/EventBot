import pdfplumber, pandas as pd

def extract_tables(path: str, max_rows: int = 20) -> list[pd.DataFrame]:
    with pdfplumber.open(path) as pdf:
        dfs = []
        for page in pdf.pages:
            for table in page.extract_tables():
                df = pd.DataFrame(table[1:], columns=table[0])
                dfs.append(df.head(max_rows))  # sample data only
        return dfs