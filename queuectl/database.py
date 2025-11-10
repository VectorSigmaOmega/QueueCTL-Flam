# queuectl/database.py
import sqlite3
import os

# We will store the database in a hidden directory in the user's home folder
APP_DIR = os.path.join(os.path.expanduser('~'), '.queuectl')
DB_PATH = os.path.join(APP_DIR, 'queue.db')
PID_FILE = os.path.join(APP_DIR, 'queuectl.pid')
# --- NEW ---
LOG_FILE = os.path.join(APP_DIR, 'worker.log') # Add a log file path


def get_db_connection():
    """
    Creates the app directory if it doesn't exist and returns
    a connection to the SQLite database.
    """
    os.makedirs(APP_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # This allows us to access columns by name (e.g., row['id'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database schema and inserts default configuration.
    """
    # --- MODIFIED ---
    # Ensure app dir exists before we do anything
    os.makedirs(APP_DIR, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create the 'jobs' table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        command TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    ''')

    # Create the 'config' table for settings
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')

    # Insert default config values (if they don't already exist)
    default_config = [
        ('max_retries', '3'),
        ('backoff_base', '2')
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
        default_config
    )

    conn.commit()
    conn.close()
    print(f"Database and config initialized at: {APP_DIR}")