import os, pathlib
from sqlalchemy import create_engine

root_dir = pathlib.Path(__file__).resolve().parent
db_file  = root_dir / "tables.db"
engine   = create_engine(f"sqlite:///{db_file}")
print(engine.url)