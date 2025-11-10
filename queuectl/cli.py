# queuectl/cli.py
import click
import json
import uuid
import os
import signal
import time
import multiprocessing
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from . import database
from . import models
from . import worker as worker_module
from . import config as config_module

def start_worker_process():
    """
    Target function for a new worker process.
    Instantiates and runs a worker.
    Includes robust logging for debugging crashes.
    """
    try:
        os.makedirs(database.APP_DIR, exist_ok=True)
        log_f = open(database.LOG_FILE, 'a')
        
        # Redirect stdout and stderr to the log file
        # This is CRITICAL for detaching from the parent terminal
        sys.stdout = log_f
        sys.stderr = log_f
        
        print(f"\n--- Starting new worker at {datetime.now(timezone.utc).isoformat()} ---")
    except Exception as e:
        print(f"Failed to open log file: {e}", file=sys.__stderr__)
        return

    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    try:
        print(f"[{worker_id}] Process started (PID: {os.getpid()}).")
        w = worker_module.Worker(worker_id)
        print(f"[{worker_id}] Worker instantiated. Starting run loop...")
        w.run()
        print(f"[{worker_id}] Run loop exited cleanly.")
        
    except KeyboardInterrupt:
        print(f"[{worker_id}] KeyboardInterrupt received.")
        pass
    except Exception as e:
        print(f"[{worker_id}] FATAL ERROR: Worker crashed.")
        traceback.print_exc(file=sys.stderr)
        print("--- End of error ---")
    finally:
        print(f"[{worker_id}] Process exiting.")
        log_f.close()


def get_running_pids():
    """Reads and returns a list of PIDs from the PID file."""
    if not os.path.exists(database.PID_FILE):
        return []
    try:
        with open(database.PID_FILE, 'r') as f:
            pids = [int(pid) for pid in f.read().splitlines() if pid.strip()]
        return pids
    except Exception as e:
        print(f"Error reading PID file: {e}")
        return []

def clear_pid_file():
    """Deletes the PID file."""
    if os.path.exists(database.PID_FILE):
        os.remove(database.PID_FILE)

def is_process_running(pid):
    """Checks if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

@click.group()
def main():
    """
    queuectl: A CLI-based background job queue system.
    """
    pass

@main.command('init-db')
def init_db_command():
    """
    Initializes the job queue database.
    """
    try:
        database.init_db()
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)

@main.command()
@click.argument('job_json_string')
def enqueue(job_json_string):
    """
    Add a new job to the queue.
    
    JOB_JSON_STRING: A JSON string defining the job.
    Example: '{"id": "job1", "command": "sleep 10"}'
    """
    try:
        job_data = json.loads(job_json_string)
        job_id = models.create_job(job_data)
        click.echo(f"Job '{job_id}' enqueued with state 'pending'.")
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON string.", err=True)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)

def print_jobs(jobs):
    """Helper function to print a list of jobs."""
    if not jobs:
        click.echo("No jobs found.")
        return
    
    click.echo(f"{'ID':<20} {'COMMAND':<25} {'STATE':<12} {'ATTEMPTS':<10} {'LAST_UPDATED':<20}")
    click.echo("-" * 87)
    for job in jobs:
        attempts = f"{job['attempts']}/{job['max_retries']}"
        click.echo(f"{job['id']:<20} {job['command']:<25} {job['state']:<12} {attempts:<10} {job['updated_at']:<20}")

@main.command()
@click.option('--state', default=None, help='Filter jobs by state (e.g., pending, failed).')
def list(state):
    """
    List jobs in the queue.
    """
    try:
        if state:
            state = state.lower()
            valid_states = ['pending', 'processing', 'completed', 'failed', 'dead']
            if state not in valid_states:
                click.echo(f"Error: Invalid state '{state}'. Must be one of {valid_states}", err=True)
                return

        jobs = models.list_jobs(state)
        print_jobs(jobs)

    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)

@main.group()
def worker():
    """
    Manage worker processes.
    """
    pass

@worker.command()
@click.option('--count', default=1, help='Number of workers to start.')
def start(count):
    """
    Start one or more workers in the background.
    """
    running_pids = get_running_pids()
    active_pids = [pid for pid in running_pids if is_process_running(pid)]
    
    if active_pids:
        click.echo(f"Workers are already running with PIDs: {active_pids}")
        click.echo("Please stop them first with 'queuectl worker stop'.")
        return

    # Use a detached subprocess to avoid multiprocessing's atexit join hang
    # We launch a small module that calls start_worker_process in a fresh interpreter
    processes = []
    cmd = [sys.executable, '-m', 'queuectl.worker_launcher']
    for _ in range(count):
        try:
            # start_new_session detaches from controlling TTY and parent process group
            p = subprocess.Popen(cmd, close_fds=True, start_new_session=True)
            processes.append(p)
        except Exception as e:
            click.echo(f"Error starting worker subprocess: {e}", err=True)

    pids_to_save = [p.pid for p in processes if p and p.pid]
    try:
        with open(database.PID_FILE, 'w') as f:
            for pid in pids_to_save:
                f.write(f"{pid}\n")
        click.echo(f"Started {count} worker(s) in the background with PIDs: {pids_to_save}")
    except Exception as e:
        click.echo(f"Error writing PID file: {e}")
        click.echo("Workers started, but PID file not written. You may need to stop them manually.")

@worker.command()
def stop():
    """
    Stop all running worker processes gracefully.
    """
    pids = get_running_pids()
    if not pids:
        click.echo("No workers running (PID file not found).")
        return

    click.echo(f"Sending graceful shutdown (SIGTERM) to PIDs: {pids}...")
    stopped_count = 0
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            stopped_count += 1
        except ProcessLookupError:
            click.echo(f"Warning: Process {pid} not found (may have already stopped).")
        except Exception as e:
            click.echo(f"Error stopping process {pid}: {e}")

    click.echo(f"Signal sent to {stopped_count} process(es).")
    clear_pid_file()
    
@main.command()
def status():
    """
    Show summary of all job states & active workers.
    """
    click.echo("--- Worker Status ---")
    running_pids = get_running_pids()
    active_pids = [pid for pid in running_pids if is_process_running(pid)]
    
    if not active_pids:
        click.echo("No active workers found.")
        if running_pids:
            click.echo("Cleaning up stale PID file.")
            clear_pid_file()
    else:
        click.echo(f"Found {len(active_pids)} active worker(s): {active_pids}")

    click.echo("\n--- Job Summary ---")
    summary = models.get_job_summary()
    click.echo(f"  Total:      {summary['total']}")
    click.echo(f"  Pending:    {summary['pending']}")
    click.echo(f"  Processing: {summary['processing']}")
    click.echo(f"  Completed:  {summary['completed']}")
    click.echo(f"  Failed:     {summary['failed']}")
    click.echo(f"  Dead (DLQ): {summary['dead']}")


@main.group()
def dlq():
    """
    Manage the Dead Letter Queue (DLQ).
    """
    pass

@dlq.command('list')
def dlq_list():
    """
    List all jobs in the DLQ.
    """
    try:
        jobs = models.list_jobs(state='dead')
        print_jobs(jobs)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)

@dlq.command('retry')
@click.argument('job_id')
def dlq_retry(job_id):
    """
    Retry a specific job from the DLQ.
    """
    try:
        models.retry_dead_job(job_id)
        click.echo(f"Job '{job_id}' moved from DLQ to 'pending' state.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)

@main.group()
def config():
    """
    Manage system configuration.
    """
    pass

@config.command('set')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    """
    Set a configuration value (e.g., max_retries, backoff_base).
    """
    try:
        config_module.set_config_value(key, value)
        click.echo(f"Config '{key}' set to '{value}'.")
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)

if __name__ == '__main__':
    main()