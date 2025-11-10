import time
from conftest import run_cmd


def test_worker_start_stop_and_status():
    # Start two workers
    res = run_cmd(["worker", "start", "--count", "2"])
    assert res.returncode == 0, res.stderr

    # Give them time to start
    time.sleep(1)

    # Status should show active workers
    res = run_cmd(["status"])
    assert res.returncode == 0
    assert "active worker(s)" in res.stdout

    # Stop and validate message
    res = run_cmd(["worker", "stop"]) 
    assert res.returncode == 0
