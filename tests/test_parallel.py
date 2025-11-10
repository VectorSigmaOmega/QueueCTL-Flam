import time
from conftest import run_cmd


def test_parallel_workers_complete_three_sleep_jobs_fast():
    # Start 3 workers
    assert run_cmd(["worker", "start", "--count", "3"]).returncode == 0
    time.sleep(1)

    # Enqueue 3 jobs that sleep 2 seconds
    assert run_cmd(["enqueue", '{"id":"p1","command":"sleep 2"}']).returncode == 0
    assert run_cmd(["enqueue", '{"id":"p2","command":"sleep 2"}']).returncode == 0
    assert run_cmd(["enqueue", '{"id":"p3","command":"sleep 2"}']).returncode == 0

    # Wait up to ~4 seconds; they should complete in parallel
    time.sleep(3)

    # All 3 done
    out = run_cmd(["list", "--state", "completed"]).stdout
    assert "p1" in out and "p2" in out and "p3" in out
