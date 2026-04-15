import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError
import logging
from dotenv import load_dotenv
load_dotenv()


class PostgresClient:
    def __init__(self):
        try:
            # Use password authentication for PostgreSQL connection
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT"),
                database=os.getenv("POSTGRES_DB"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                sslmode='require'
            )
            self.conn.autocommit = True
            logging.info("Successfully connected to PostgreSQL using password authentication")
        except OperationalError as e:
            raise RuntimeError(f"Database connection failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during DB connection: {e}")  

    def execute_query(self, query, params=None):
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            self.conn.commit()


    def fetch_one(self, query, params=None):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()
        
        
    def fetch_all(self, query, params=None):
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except psycopg2.OperationalError as oe:
            error_message = f"Operational error: {oe}"
            return error_message
        except Exception as e:
            error_msg = "Error in PG Service: " + str(e)
            logging.exception(error_msg)
            return error_msg

    def close(self):
        self.cursor.close()
        self.conn.close()


    