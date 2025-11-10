# queuectl/cli.py
import click
import json
import uuid
from . import database
from . import models
from . import worker as worker_module
# --- FIX: Rename the import to avoid conflict ---
from . import config as config_module

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
    Start one or more worker processes.
    """
    if count > 1:
        click.echo("Multi-worker support is not yet implemented. Starting 1 worker.")
    
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    
    try:
        w = worker_module.Worker(worker_id)
        w.run()
    except KeyboardInterrupt:
        click.echo(f"\nCaught interrupt, stopping worker {worker_id}...")

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

# --- This command group is named 'config' ---
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
        # --- FIX: Use the renamed 'config_module' here ---
        config_module.set_config_value(key, value)
        click.echo(f"Config '{key}' set to '{value}'.")
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)

if __name__ == '__main__':
    main()