from pydantic import BaseModel

class Column(BaseModel):
    name: str
    type: str
    description: str

class TableSchema(BaseModel):
    table_name: str
    columns: list[Column]
    primary_key: str | None
    notes: str