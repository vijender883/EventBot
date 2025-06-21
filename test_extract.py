from table_extraction.extractor import extract_tables
import pandas as pd, pprint, sys, pathlib

pdf = pathlib.Path(sys.argv[1]).resolve()
for i, df in enumerate(extract_tables(str(pdf))):
    print(i, df.shape)
    pprint.pp(df.head().to_dict(orient="list"))
