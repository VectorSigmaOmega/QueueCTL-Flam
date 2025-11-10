import time
import signal
from . import models
from . import executor

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
        # When SIGTERM is received, call self.handle_shutdown
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        # Also handle KeyboardInterrupt (Ctrl+C) gracefully
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """
        Signal handler to initiate a graceful shutdown.
        """
        print(f"Worker {self.worker_id} received shutdown signal {signum}. Finishing current job...")
        self.running = False

    def run(self):
        """The main worker loop."""
        while self.running:
            job = None
            try:
                # 1. Atomically fetch a job (now supports backoff)
                job = models.atomically_get_next_job(self.worker_id)

                if job:
                    print(f"Worker {self.worker_id} picked up job {job['id']}: {job['command']}")
                    exit_code = executor.execute_job_command(job['command'])
                    if exit_code == 0:
                        models.update_job_state(job['id'], 'completed')
                        print(f"Worker {self.worker_id} completed job {job['id']}")
                    else:
                        current_attempts = job['attempts'] + 1
                        max_retries = job['max_retries']
                        
                        if current_attempts >= max_retries:
                            models.update_job_state(job['id'], 'dead', increment_attempts=True)
                            print(f"Worker {self.worker_id} moved job {job['id']} to DLQ (attempts: {current_attempts}/{max_retries})")
                        else:
                            models.update_job_state(job['id'], 'failed', increment_attempts=True)
                            print(f"Worker {self.worker_id} failed job {job['id']}, will retry (attempts: {current_attempts}/{max_retries})")

                else:
                    if self.running:
                        time.sleep(1)

            except Exception as e:
                if self.running:
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
                    time.sleep(1) # Wait after an error

        print(f"Worker {self.worker_id} shutting down.")