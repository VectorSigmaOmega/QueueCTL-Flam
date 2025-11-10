from . import database

DEFAULT_CONFIG = {
    'max_retries': 3,
    'backoff_base': 2,
}

def _normalize_key(key: str) -> str:
    """Normalize config keys to a canonical form used in the DB.
    - lowercases
    - converts hyphens to underscores
    - trims surrounding whitespace
    """
    if key is None:
        return key
    return key.strip().lower().replace('-', '_')

def get_config_value(key: str):
    """
    Fetches a configuration value from the database.
    Returns the default value if not found.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    norm_key = _normalize_key(key)
    alt_key = None
    if norm_key and '_' in norm_key:
        alt_key = norm_key.replace('_', '-')
    
    try:
        cursor.execute("SELECT value FROM config WHERE key = ?", (norm_key,))
        row = cursor.fetchone()
        if not row and alt_key:
            cursor.execute("SELECT value FROM config WHERE key = ?", (alt_key,))
            legacy_row = cursor.fetchone()
            if legacy_row:
                try:
                    cursor.execute(
                        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                        (norm_key, legacy_row['value'])
                    )
                    cursor.execute("DELETE FROM config WHERE key = ?", (alt_key,))
                    conn.commit()
                except Exception:
                    conn.rollback()
                row = legacy_row
        
        if row:
            if norm_key in ['max_retries', 'backoff_base']:
                return int(row['value'])
            return row['value']
        else:
            return DEFAULT_CONFIG.get(norm_key)
            
    except Exception as e:
        print(f"Error fetching config '{key}': {e}")
        return DEFAULT_CONFIG.get(norm_key)
    finally:
        conn.close()

def set_config_value(key: str, value: str):
    """
    Sets a configuration value in the database.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    norm_key = _normalize_key(key)
    
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (norm_key, str(value))
        )
        conn.commit()
    except Exception as e:
        print(f"Error setting config '{key}': {e}")
        conn.rollback()
    finally:
        conn.close()

def list_config() -> dict:
    """
    Returns a dictionary of effective configuration values, merging DB values
    (normalized) with defaults. Numeric config values are returned as ints.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    keys = set(DEFAULT_CONFIG.keys())
    try:
        cursor.execute("SELECT key FROM config")
        rows = cursor.fetchall()
        for row in rows:
            keys.add(_normalize_key(row['key']))
    except Exception:
        pass
    finally:
        conn.close()

    result = {}
    for k in sorted(keys):
        result[k] = get_config_value(k)
    return result