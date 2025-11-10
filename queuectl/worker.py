# queuectl/worker.py
import time
import signal
from . import models
from . import executor
# No config import needed here, models handles it

class Worker:
    """
    A worker process that fetches and executes jobs.
    """
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.running = True
        self.setup_signal_handlers()
        print(f"Worker {self.worker_id} starting...")

    def setup_signal_handlers(self):
        """Sets up signal handlers for graceful shutdown."""
        pass

    def run(self):
        """The main worker loop."""
        while self.running:
            job = None
            try:
                # 1. Atomically fetch a job (now supports backoff)
                job = models.atomically_get_next_job(self.worker_id)

                if job:
                    print(f"Worker {self.worker_id} picked up job {job['id']}: {job['command']}")
                    
                    # 2. Execute the job command
                    exit_code = executor.execute_job_command(job['command'])
                    
                    # 3. Update job state based on exit code
                    if exit_code == 0:
                        models.update_job_state(job['id'], 'completed')
                        print(f"Worker {self.worker_id} completed job {job['id']}")
                    else:
                        # --- RETRY/DLQ LOGIC ---
                        current_attempts = job['attempts'] + 1
                        max_retries = job['max_retries']
                        
                        if current_attempts >= max_retries:
                            # Move to Dead Letter Queue
                            models.update_job_state(job['id'], 'dead', increment_attempts=True)
                            print(f"Worker {self.worker_id} moved job {job['id']} to DLQ (attempts: {current_attempts}/{max_retries})")
                        else:
                            # Mark as 'failed' for retry
                            models.update_job_state(job['id'], 'failed', increment_attempts=True)
                            print(f"Worker {self.worker_id} failed job {job['id']}, will retry (attempts: {current_attempts}/{max_retries})")

                else:
                    time.sleep(1)

            except Exception as e:
                print(f"Worker {self.worker_id} encountered an error: {e}")
                if job:
                    try:
                        # On unexpected error, treat as a failure/retry
                        if (job['attempts'] + 1) >= job['max_retries']:
                            models.update_job_state(job['id'], 'dead', increment_attempts=True)
                        else:
                            models.update_job_state(job['id'], 'failed', increment_attempts=True)
                    except Exception as db_e:
                        print(f"Worker {self.worker_id} failed to update job state: {db_e}")
                time.sleep(1)

        print(f"Worker {self.worker_id} shutting down.")