# queuectl/config.py
from . import database

DEFAULT_CONFIG = {
    'max_retries': 3,
    'backoff_base': 2,
}

def get_config_value(key: str):
    """
    Fetches a configuration value from the database.
    Returns the default value if not found.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        if row:
            # Config values are stored as text, cast them
            if key in ['max_retries', 'backoff_base']:
                return int(row['value'])
            return row['value']
        else:
            # Return default if not in DB
            return DEFAULT_CONFIG.get(key)
            
    except Exception as e:
        print(f"Error fetching config '{key}': {e}")
        return DEFAULT_CONFIG.get(key)
    finally:
        conn.close()

def set_config_value(key: str, value: str):
    """
    Sets a configuration value in the database.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()
    except Exception as e:
        print(f"Error setting config '{key}': {e}")
        conn.rollback()
    finally:
        conn.close()