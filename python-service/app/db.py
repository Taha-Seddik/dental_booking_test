from typing import Generator
import psycopg2
from psycopg2.extras import RealDictCursor
from .core import config

def db_conn():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        dbname=config.DB_NAME,
    )

def dict_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)
