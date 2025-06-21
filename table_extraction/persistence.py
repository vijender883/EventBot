import os, json, itertools
from sqlalchemy import create_engine, MetaData, Table, Column, VARCHAR, FLOAT, INTEGER, JSON, inspect
from .schema_models import TableSchema
import pandas as pd

TYPE_MAP = {"string": VARCHAR, "float": FLOAT, "int": INTEGER, "date": VARCHAR}
engine = create_engine(os.getenv("DATABASE_URL"))
meta = MetaData()

def _unique_names(names):
    seen = {}
    out = []
    for base in names:
        base = str(base or "").strip()
        base = base if base and base.lower() != "none" else "col"
        cnt  = seen.get(base, 0)
        new  = base if cnt == 0 else f"{base}_{cnt}"
        seen[base] = cnt + 1
        out.append(new)
    return out

def save_table(df: pd.DataFrame, schema_json: dict):
    sch = TableSchema(**schema_json)

    desired = [c.name for c in sch.columns]
    current = list(df.columns)
    if len(desired) < len(current):
        desired += [f"col_{i}" for i in range(len(current) - len(desired))]
    elif len(desired) > len(current):
        desired = desired[: len(current)]

    df.columns = _unique_names(desired)

    insp = inspect(engine)
    if insp.has_table(sch.table_name):
        Table(sch.table_name, meta, autoload_with=engine).drop(engine)

    # -----------------------------------------------------------
    # ⬇️  remove the stale definition cached in this MetaData
    if sch.table_name in meta.tables:
        meta.remove(meta.tables[sch.table_name])
    # -----------------------------------------------------------

    cols = [
        Column(name, TYPE_MAP.get(sch.columns[i % len(sch.columns)].type, VARCHAR))
        for i, name in enumerate(df.columns)
    ]
    tbl = Table(sch.table_name, meta, *cols)   # no InvalidRequestError now
    tbl.create(engine)

    df.to_sql(sch.table_name, engine, if_exists="append", index=False)

    meta_tbl = Table(
        "extracted_table_meta",
        meta,
        Column("table_name", VARCHAR, primary_key=True),
        Column("schema", JSON),
        extend_existing=True,
    )
    meta_tbl.create(engine, checkfirst=True)

    with engine.begin() as conn:
        conn.execute(meta_tbl.delete().where(meta_tbl.c.table_name == sch.table_name))
        conn.execute(
            meta_tbl.insert().values(
                table_name=sch.table_name, schema=json.loads(sch.json())
            )
        )


