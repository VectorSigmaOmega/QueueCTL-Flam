# queuectl/models.py
import json
import sqlite3
import math # Import math for power calculation
from datetime import datetime, timezone # Import timezone
from . import database
from . import config # Import the new config module

def create_job(job_data: dict):
    """
    Creates a new job in the database.
    """
    if 'id' not in job_data or 'command' not in job_data:
        raise ValueError("Job data must include 'id' and 'command'")

    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Use timezone-aware datetime
    now = datetime.now(timezone.utc).isoformat()
    
    max_retries = job_data.get('max_retries')
    if max_retries is None:
        max_retries = config.get_config_value('max_retries')

    try:
        cursor.execute(
            """
            INSERT INTO jobs (id, command, max_retries, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                job_data['id'],
                job_data['command'],
                max_retries,
                now,
                now
            )
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Job with ID '{job_data['id']}' already exists.")
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e
    
    conn.close()
    return job_data['id']

def list_jobs(state: str = None):
    """
    Lists all jobs, optionally filtering by state.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, command, state, attempts, max_retries, updated_at FROM jobs"
    params = []

    if state:
        query += " WHERE state = ?"
        params.append(state)
    
    query += " ORDER BY created_at ASC"

    cursor.execute(query, tuple(params))
    jobs = cursor.fetchall()
    conn.close()
    
    return [dict(job) for job in jobs]

# --- UPDATED FUNCTION ---
def atomically_get_next_job(worker_id: str):
    """
    Atomically fetches the next 'pending' job OR a 'failed' job
    that is ready to be retried based on exponential backoff.
    """
    conn = database.get_db_connection()
    conn.execute("BEGIN IMMEDIATE TRANSACTION")
    cursor = conn.cursor()
    
    try:
        # Load config values needed for the query
        backoff_base = config.get_config_value('backoff_base')
        
        # Get current time in UTC as a Unix timestamp
        now_timestamp = datetime.now(timezone.utc).timestamp()
        
        # This query is complex:
    # 1. Select any 'pending' job.
    # 2. Select any 'failed' job WHERE retry is due using exponential backoff:
    #    delay = (backoff_base ^ attempts) seconds
    #    current_time > updated_at_time + POW(backoff_base, attempts)
        # 3. Order by creation time to process oldest jobs first.
        
        # Note: SQLite doesn't have a POWER() function by default.
        # We must register our own.
        conn.create_function("POW", 2, math.pow)
        
        # We use strftime('%s', updated_at) to convert ISO timestamp to Unix time
        # We must also cast it to an INTEGER
        query = f"""
            SELECT id FROM jobs
            WHERE state = 'pending'
            OR (
                state = 'failed' AND
                {now_timestamp} > (CAST(strftime('%s', updated_at) AS INTEGER) + POW(?, attempts))
            )
            ORDER BY created_at ASC
            LIMIT 1
        """

        cursor.execute(query, (backoff_base,))
        job_row = cursor.fetchone()

        if job_row:
            job_id = job_row['id']
            now_iso = datetime.now(timezone.utc).isoformat()
            
            cursor.execute(
                """
                UPDATE jobs 
                SET state = 'processing', updated_at = ?
                WHERE id = ?
                """,
                (now_iso, job_id)
            )
            
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            full_job_data = cursor.fetchone()
            
            conn.commit()
            return dict(full_job_data)
        else:
            conn.commit()
            return None

    except sqlite3.OperationalError as e:
        print(f"Worker {worker_id}: Database locked, rolling back. {e}")
        conn.rollback()
        return None
    except Exception as e:
        print(f"Worker {worker_id}: Error getting next job: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

# --- UPDATED FUNCTION ---
def update_job_state(job_id: str, state: str, increment_attempts: bool = False):
    """
    Updates the state and 'updated_at' timestamp of a job.
    Optionally increments the attempt counter.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    try:
        if increment_attempts:
            cursor.execute(
                """
                UPDATE jobs
                SET state = ?, updated_at = ?, attempts = attempts + 1
                WHERE id = ?
                """,
                (state, now, job_id)
            )
        else:
            cursor.execute(
                """
                UPDATE jobs
                SET state = ?, updated_at = ?
                WHERE id = ?
                """,
                (state, now, job_id)
            )
        conn.commit()
    except Exception as e:
        print(f"Error updating job {job_id}: {e}")
        conn.rollback()
    finally:
        conn.close()

# --- NEW FUNCTION ---
def retry_dead_job(job_id: str):
    """
    Moves a job from the 'dead' state back to 'pending' and resets its attempts.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    try:
        # Check if the job is actually in the 'dead' state
        cursor.execute("SELECT state FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        
        if not job:
            raise ValueError(f"Job with ID '{job_id}' not found.")
        
        if job['state'] != 'dead':
            raise ValueError(f"Job '{job_id}' is in state '{job['state']}', not 'dead'.")

        # Reset the job
        cursor.execute(
            """
            UPDATE jobs
            SET state = 'pending', attempts = 0, updated_at = ?
            WHERE id = ?
            """,
            (now, job_id)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
             raise ValueError(f"Job with ID '{job_id}' not found in 'dead' state.")
        
    except Exception as e:
        conn.rollback()
        raise e # Re-raise the exception to be caught by the CLI
    finally:
        conn.close()

        
def get_job_summary():
    """
    Returns a dictionary with the count of jobs in each state.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    summary = {
        'pending': 0,
        'processing': 0,
        'completed': 0,
        'failed': 0,
        'dead': 0,
        'total': 0,
    }
    
    try:
        cursor.execute("SELECT state, COUNT(*) FROM jobs GROUP BY state")
        rows = cursor.fetchall()
        for row in rows:
            if row['state'] in summary:
                summary[row['state']] = row['COUNT(*)']
            summary['total'] += row['COUNT(*)']
        return summary
    except Exception as e:
        print(f"Error getting job summary: {e}")
        return summary
    finally:
        conn.close()