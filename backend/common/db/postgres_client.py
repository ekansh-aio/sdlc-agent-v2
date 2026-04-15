import os
import psycopg2
import logging
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

#from common.secrets.key_vault_client import KeyVaultClient

class PostgresClient:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def _ensure_connected(self):
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    host=os.getenv("POSTGRES_HOST"),
                    port=os.getenv("POSTGRES_PORT"),
                    database=os.getenv("POSTGRES_DB"),
                    user=os.getenv("POSTGRES_USER"),
                    password=os.getenv("POSTGRES_PASSWORD"),
                    sslmode='require'
                )
                self.cursor = self.conn.cursor()
                logging.info("Successfully connected to PostgreSQL using password authentication")
            except Exception as e:
                logging.error(f"PostgreSQL connection failed: {str(e)}")
                raise

    def execute_query(self, query, params=None):
        self._ensure_connected()
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            self.conn.commit()

    def fetch_one(self, query, params=None):
        self._ensure_connected()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def fetch_all(self, query, params=None):
        self._ensure_connected()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def close(self):
        self.cursor.close()
        self.conn.close()


