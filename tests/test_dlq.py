import time
from conftest import run_cmd


def test_failed_job_moves_to_dlq_and_retry():
    # Make retries quick and deterministic
    assert run_cmd(["config", "set", "max_retries", "2"]).returncode == 0
    assert run_cmd(["config", "set", "backoff_base", "1"]).returncode == 0

    # Start a single worker
    assert run_cmd(["worker", "start", "--count", "1"]).returncode == 0
    time.sleep(1)

    # Enqueue a failing job
    job_json = '{"id": "dlq_job", "command": "exit 1"}'
    assert run_cmd(["enqueue", job_json]).returncode == 0

    # Wait for it to fail twice and move to DLQ (1s + 2s backoff, ~3s total)
    time.sleep(4)

    # Verify in DLQ with attempts 2/2
    res = run_cmd(["dlq", "list"]).stdout
    assert "dlq_job" in res
    assert "2/2" in res

    # Retry from DLQ -> back to pending with 0/2
    assert run_cmd(["dlq", "retry", "dlq_job"]).returncode == 0
    time.sleep(0.5)
    res = run_cmd(["list", "--state", "pending"]).stdout
    assert "dlq_job" in res
    assert "0/2" in res
