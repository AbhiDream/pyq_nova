import psycopg2
import psycopg2.extras
import psycopg2.pool
import logging
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT, DATABASE_URL

logger = logging.getLogger(__name__)

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def create_pool():
    global _pool
    if DATABASE_URL:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=DATABASE_URL
        )
        logger.info("[DB] psycopg2 ThreadedConnectionPool created using DATABASE_URL.")
    else:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
        )
        logger.info("[DB] psycopg2 ThreadedConnectionPool created using local credentials.")


def close_pool():
    global _pool
    if _pool:
        _pool.closeall()
        logger.info("[DB] Connection pool closed.")


def get_conn():
    """Borrow a connection from the pool."""
    if _pool is None:
        raise RuntimeError("DB pool not initialised.")
    return _pool.getconn()


def put_conn(conn):
    """Return a connection to the pool."""
    if _pool:
        _pool.putconn(conn)


class db_cursor:
    """Context manager: borrows a connection, yields a DictCursor, returns on exit."""
    def __enter__(self):
        self.conn = get_conn()
        self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return self.cur

    def __exit__(self, exc_type, *_):
        if exc_type:
            self.conn.rollback()
        self.cur.close()
        put_conn(self.conn)
