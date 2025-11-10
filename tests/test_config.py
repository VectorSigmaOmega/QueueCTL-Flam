import os
import subprocess
import json

# Helper to run queuectl and capture output

def run_cmd(args):
    result = subprocess.run(["queuectl", *args], capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def setup_module(module):
    # Fresh DB per test module
    db_path = os.path.expanduser("~/.queuectl/queue.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    code, out, err = run_cmd(["init-db"])  # ensure DB exists
    assert code == 0


def test_set_and_get_hyphenated_max_retries():
    code, out, err = run_cmd(["config", "set", "max-retries", "5"])  # hyphenated form
    assert code == 0
    assert "max-retries" in out

    # Retrieve via underscore form
    code, out, err = run_cmd(["config", "get", "max_retries"])  # underscore form
    assert code == 0
    assert "max_retries" in out or "max-retries" in out
    assert out.endswith("5") or out.split()[-1] == "5"


def test_set_and_get_backoff_base_hyphen():
    code, out, err = run_cmd(["config", "set", "backoff-base", "7"])  # hyphen form
    assert code == 0

    code, out, err = run_cmd(["config", "get", "backoff_base"])  # underscore
    assert code == 0
    assert out.endswith("7")


def test_config_list_contains_expected_keys():
    code, out, err = run_cmd(["config", "list"])
    assert code == 0
    # Should include normalized keys
    assert "max_retries" in out
    assert "backoff_base" in out


def test_job_creation_uses_updated_max_retries():
    # Set new max retries
    code, out, err = run_cmd(["config", "set", "max_retries", "6"])  # underscore form
    assert code == 0

    # Enqueue job without explicit max_retries; should inherit 6
    job_json = '{"id": "cfg_job", "command": "echo hi"}'
    code, out, err = run_cmd(["enqueue", job_json])
    assert code == 0

    # List jobs and check attempts column pattern 0/6
    code, out, err = run_cmd(["list"])  # plain list
    assert code == 0
    # Find line for cfg_job and ensure it has /6
    lines = out.splitlines()
    matching = [ln for ln in lines if "cfg_job" in ln]
    assert matching, f"Job cfg_job not found in output: {out}"
    assert any("/6" in ln for ln in matching)
