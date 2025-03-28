from ..config import (
    settings,
)
from databases import Database

db_conn_string = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
database = Database(db_conn_string, min_size=5, max_size=20)

def create_database() -> Database:
    db_conn_string = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    print("db_conn_string", db_conn_string)
    return Database(db_conn_string, min_size=5, max_size=20)