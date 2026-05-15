import logging
import psycopg2
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
        )
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                google_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                picture TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_login TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        # Create user_progress table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                question_id TEXT NOT NULL,
                status TEXT, -- 'correct', 'wrong', 'skipped'
                selected_option TEXT,
                last_attempt_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id, question_id)
            );
        """)
        
        conn.commit()
        cur.close()
        logger.info("Migrations ran successfully. Tables 'users' and 'user_progress' are ready.")
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migrations()
