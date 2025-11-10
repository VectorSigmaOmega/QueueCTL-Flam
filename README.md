# QueueCTL

`queuectl` is a CLI-based background job queue system built in Python.

It manages background jobs with multiple worker processes, handles retries using exponential backoff, and maintains a Dead Letter Queue (DLQ) for permanently failed jobs.

---

## 1) Setup

1. Clone and enter the repo
     ```bash
     git clone https://github.com/VectorSigmaOmega/QueueCTL-Flam.git
     cd QueueCTL-Flam
     ```
2. Install dependencies
    ```bash
    python -m pip install -r requirements.txt
    ```
3. Install the CLI
    ```bash
    python -m pip install .
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
    #   Total: ... 
    #   Pending: ...
    #   Processing: ...
    #   Completed: ... 
    #   Failed: ...
    #   Dead (DLQ): ...
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
    queuectl config set backoff_base 2 
    ```

---

## 3) Project structure and file roles

Project tree:

```text
QueueCTL-Flam/
├─ README.md
├─ demo_script.sh           
├─ requirements.txt           
├─ setup.py                
└─ queuectl/
    ├─ __init__.py            
    ├─ cli.py                 
    ├─ config.py               
    ├─ database.py        
    ├─ executor.py             
    ├─ models.py              
    ├─ worker.py               
    └─ worker_launcher.py    
```

Purpose of files:
- `setup.py`: Allows `python -m pip install .` and exposes the `queuectl` command.
- `demo_script.sh`: End-to-end script demonstrating success, retries/backoff, DLQ, persistence, multi-worker.
- `queuectl/cli.py`: CLI entry point and command definitions.
- `queuectl/models.py`: Core job lifecycle operations and backoff logic.
- `queuectl/worker.py`: Background worker behavior and signal handling.
- `queuectl/database.py`: Storage configuration and schema setup.
- `queuectl/config.py`: Configuration storage and normalization.
- `queuectl/executor.py`: Command execution helper.
- `queuectl/worker_launcher.py`: Helper to spawn workers detached from the CLI.

---

## 4) Architecture Overview

- Storage: SQLite database at `~/.queuectl/queue.db` with two tables:
    - `jobs(id, command, state, attempts, max_retries, created_at, updated_at)`
    - `config(key, value)`
- Workers: Separate background processes started via a launcher. Each worker:
    - Selects the next job inside a transaction.
    - Executes the shell `command` and uses exit code to determine success/failure.
    - On failure, increments `attempts` and marks `failed` (or `dead` if attempts reached `max_retries`).
    - Handles SIGTERM/SIGINT to finish current iteration and exit cleanly.
- Backoff: Exponential retry delay based on the formula: $\text{delay} = \text{base}^\text{attempts}$ seconds.
- DLQ: Jobs moved to `dead` after exhausting retries are listed via `queuectl dlq list`; they can be retried with `queuectl dlq retry <id>` (resets attempts to 0 and state to pending).

---

## 5) Job Lifecycle

1. Enqueued: `pending`
2. Picked by a worker: `processing`
3. Execution result:
     - exit code 0: `completed`
     - exit code != 0: `failed` (will be retried after backoff)
4. When `attempts >= max_retries`: move to `dead` (DLQ)


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

## 7) Demo script

Purpose: Run a quick end-to-end demonstration script to verify the main flows of assignment.

How to run:

```bash
bash ./demo_script.sh
```

---
