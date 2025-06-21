from sqlalchemy import create_engine, MetaData, Table, Column, VARCHAR, FLOAT, INTEGER
from sqlalchemy.dialects.postgresql import JSONB
from schema_models import TableSchema
import os

TYPE_MAP = {"string": VARCHAR, "float": FLOAT, "int": INTEGER, "date": VARCHAR}
engine = create_engine(os.getenv("DATABASE_URL"))
meta = MetaData(bind=engine)

def save_table(df, schema_json):
    sch = TableSchema(**schema_json)
    cols = [Column(c.name, TYPE_MAP.get(c.type, VARCHAR)) for c in sch.columns]
    tbl = Table(sch.table_name, meta, *cols, extend_existing=True)
    tbl.create(checkfirst=True)
    df.to_sql(sch.table_name, engine, if_exists="append", index=False)

    meta_tbl = Table(
        "extracted_table_meta", meta,
        Column("table_name", VARCHAR, primary_key=True),
        Column("schema", JSONB),
        extend_existing=True
    )
    meta_tbl.create(checkfirst=True)
    with engine.begin() as conn:
        conn.execute(
            meta_tbl.insert()
            .values(table_name=sch.table_name, schema=schema_json)
            .on_conflict_do_update(
                index_elements=['table_name'],
                set_={"schema": schema_json}
            )
        )
