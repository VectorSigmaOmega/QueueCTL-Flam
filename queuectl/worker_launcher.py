# queuectl/worker_launcher.py
"""Module entry point for spawning a detached worker process.
This is invoked via: python -m queuectl.worker_launcher
It isolates worker startup from the CLI process so the CLI can exit
immediately without waiting for multiprocessing joins.
"""
from .cli import start_worker_process

if __name__ == '__main__':
    start_worker_process()
