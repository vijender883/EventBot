# import pdfplumber, pandas as pd

# def extract_tables(path: str, max_rows: int = 20) -> list[pd.DataFrame]:
#     with pdfplumber.open(path) as pdf:
#         dfs = []
#         for page in pdf.pages:
#             for table in page.extract_tables():
#                 df = pd.DataFrame(table[1:], columns=table[0])
#                 dfs.append(df.head(max_rows))  # sample data only
#         return dfs

import camelot, pandas as pd, pdfplumber

def _camelot_tables(path: str):
    # lattice = detect ruled tables; stream = text-flow tables
    return camelot.read_pdf(path, pages="all", flavor="lattice")

def extract_tables(path: str, max_rows: int = 20, max_cols: int = 12):
    dfs = []

    # 1️⃣ Camelot first – best for numeric LED tables
    for t in _camelot_tables(path):
        df = t.df                       # first row is header
        header, body = df.iloc[0], df.iloc[1:]
        body.columns = header
        body = body.iloc[:max_rows, :max_cols]
        dfs.append(body.reset_index(drop=True))

    # 2️⃣ pdfplumber fallback for anything Camelot missed
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                df = pd.DataFrame(table[1:], columns=table[0])
                dfs.append(df.iloc[:max_rows, :max_cols])

    return dfs