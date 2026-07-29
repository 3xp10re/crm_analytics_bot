import os
from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

@contextmanager
def get_postgres_connection() -> Generator[Connection,None,None,]:
    connection = psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        connect_timeout=5,
        row_factory=dict_row,
    )

    try:
        yield connection
    finally:
        connection.close()