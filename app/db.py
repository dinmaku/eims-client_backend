# db.py
import os
import pg8000
import logging
from urllib.parse import urlparse
import ssl
from dotenv import load_dotenv

# Load .env locally, ignored in Render
load_dotenv()

logger = logging.getLogger(__name__)

def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")

    url = urlparse(DATABASE_URL)

    # SSL required for external Render DB
    ssl_context = None
    if url.hostname not in ("localhost", "127.0.0.1") and not url.hostname.endswith(".render.internal"):
        ssl_context = ssl.create_default_context()

    try:
        logger.info(f"Connecting to database at {url.hostname}...")
        conn = pg8000.connect(
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port or 5432,
            database=url.path[1:],  # remove leading '/'
            ssl_context=ssl_context
        )

        # Set search path to public schema
        cursor = conn.cursor()
        cursor.execute("SET search_path TO public")
        cursor.close()

        logger.info("Database connection successful")
        return conn

    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
