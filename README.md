# QueueCTL - A CLI Job Queue System

`queuectl` is a minimal, production-grade, CLI-based background job queue system built in Python.

It manages background jobs with multiple worker processes, handles retries using exponential backoff, and maintains a Dead Letter Queue (DLQ) for permanently failed jobs.

**Demo Video:** [Add link here]

---

## 1) Setup

1. Clone and enter the repo
     ```bash
     git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
     cd YOUR_REPO_NAME
     ```
2. Install dependencies
     ```bash
     pip install -r requirements.txt
     ```
3. Install the CLI (editable)
     ```bash
     pip install -e .
     ```
4. Initialize the database (creates `~/.queuectl/queue.db`)
     ```bash
     queuectl init-db
     ```

---

## 2) CLI Command Reference with Examples

- Enqueue a job
    ```bash
    queuectl enqueue '{"id":"job1","command":"echo Hello"}'
    ```

- Start workers (background)
    ```bash
    queuectl worker start --count 3
    # -> Started 3 worker(s) in the background with PIDs: [12345, 12346, 12347]
    ```

- Stop workers (graceful)
    ```bash
    queuectl worker stop
    # -> Signal sent to N process(es).
    ```

- Show system status
    ```bash
    queuectl status
    # --- Worker Status ---
    # Found 3 active worker(s): [...]
    # --- Job Summary ---
    #   Total: ... Pending: ... Processing: ... Completed: ... Failed: ... Dead (DLQ): ...
    ```

- List jobs (all or by state)
    ```bash
    queuectl list
    queuectl list --state pending
    queuectl list --state completed
    ```

- DLQ operations
    ```bash
    queuectl dlq list
    queuectl dlq retry job1
    ```

- Configuration
    ```bash
    queuectl config list
    queuectl config get max_retries
    queuectl config set max_retries 4
    queuectl config set backoff_base 2   # hyphenated forms also work
    ```

---

## 3) Architecture Overview

- Storage: SQLite database at `~/.queuectl/queue.db` with two tables:
    - `jobs(id, command, state, attempts, max_retries, created_at, updated_at)`
    - `config(key, value)`
- Workers: Separate background processes started via a launcher. Each worker:
    - Atomically selects the next job inside a transaction.
    - Executes the shell `command` and uses exit code to determine success/failure.
    - On failure, increments `attempts` and marks `failed` (or `dead` if attempts reached `max_retries`).
    - Handles SIGTERM/SIGINT to finish current iteration and exit cleanly.
- Backoff: Exponential retry delay based on the configured base: delay = base^attempts seconds.
- DLQ: Jobs moved to `dead` after exhausting retries are listed via `queuectl dlq list`; they can be retried with `queuectl dlq retry <id>` (resets attempts to 0 and state to pending).

---

## 4) Job Lifecycle

1. Enqueued: `pending`
2. Picked by a worker: `processing`
3. Execution result:
     - exit code 0: `completed`
     - exit code != 0: `failed` (will be retried after backoff)
4. When `attempts >= max_retries`: move to `dead` (DLQ)

---

## 5) Assumptions & Trade-offs

- Exponential backoff formula required by the assignment is: delay = base^attempts seconds.
    - Default `backoff_base = 2` yields delays: 1st retry after 2s, then 4s, 8s, ...
    - You can change the base with `queuectl config set backoff_base <n>`.
- Jobs stuck in `processing` due to abrupt worker termination are not automatically re-queued in this version.
    - For the assignment scope, this is acceptable; a future enhancement could implement a processing lease/timeout.
- Commands are executed with `shell=True`; ensure inputs are trusted in your environment.

---

## 6) Manual Testing Instructions

Until automated tests are reintroduced, you can validate core flows manually:

```bash
# Init
queuectl init-db

# Start 2 workers
queuectl worker start --count 2

# Successful job
queuectl enqueue '{"id":"ok1","command":"echo OK"}'
sleep 2 && queuectl list --state completed

# Configure quick retries (example)
queuectl config set max_retries 2
queuectl config set backoff_base 1

# Failing job -> DLQ
queuectl enqueue '{"id":"bad1","command":"exit 1"}'
sleep 3 && queuectl dlq list

# Retry a DLQ job
queuectl dlq retry bad1
queuectl list --state pending

# Stop workers
queuectl worker stop
```

---

## 7) What’s Next

- Reintroduce minimal automated tests later.
- Optional improvements: processing lease, structured logging, additional admin commands (purge, show).