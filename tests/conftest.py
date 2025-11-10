import os
import subprocess
import time
import pytest

HOME = os.path.expanduser("~")
APP_DIR = os.path.join(HOME, ".queuectl")
DB_PATH = os.path.join(APP_DIR, "queue.db")
PID_FILE = os.path.join(APP_DIR, "queuectl.pid")


def run_cmd(args):
    # Avoid timeouts for short-lived CLI commands like worker start/stop
    # Capture output for assertions
    return subprocess.run(["queuectl", *args], capture_output=True, text=True)


def stop_workers_quietly():
    try:
        run_cmd(["worker", "stop"])  # ignore result
    except Exception:
        pass


def remove_state():
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def fresh_env_per_test():
    # Ensure clean state before each test
    stop_workers_quietly()
    remove_state()
    # Init DB
    res = run_cmd(["init-db"])
    assert res.returncode == 0, res.stderr
    yield
    # Cleanup after each test
    stop_workers_quietly()
    remove_state()
