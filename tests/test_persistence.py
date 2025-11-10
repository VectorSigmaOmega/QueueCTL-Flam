import time
from conftest import run_cmd


def test_job_persists_across_worker_restart():
    # Start workers
    assert run_cmd(["worker", "start", "--count", "1"]).returncode == 0
    time.sleep(1)
    # Stop workers
    assert run_cmd(["worker", "stop"]).returncode == 0
    time.sleep(0.5)

    # Enqueue job while stopped
    job_json = '{"id": "persist_job", "command": "echo PERSIST"}'
    assert run_cmd(["enqueue", job_json]).returncode == 0

    # Restart worker
    assert run_cmd(["worker", "start", "--count", "1"]).returncode == 0
    time.sleep(2)

    # Should complete
    res = run_cmd(["list", "--state", "completed"]).stdout
    assert "persist_job" in res
