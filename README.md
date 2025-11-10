# QueueCTL - A CLI Job Queue System

`queuectl` is a minimal, production-grade, CLI-based background job queue system built in Python.

It manages background jobs with multiple worker processes, handles retries using exponential backoff, and maintains a Dead Letter Queue (DLQ) for permanently failed jobs.

**Demo Video:** [Link to your CLI demo video on Google Drive/Loom]

---

## 1. Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME)
    cd YOUR_REPO_NAME
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install the CLI:**
    This command uses `setup.py` to make the `queuectl` command available system-wide (in your current environment). The `-e` flag (editable) means any changes you make to the code are immediately reflected.
    ```bash
    pip install -e .
    ```

4.  **Initialize the database:**
    This creates the SQLite database and config file in `~/.queuectl/`.
    ```bash
    queuectl init-db
    ```

---

## 2. Usage Examples

### Worker Management

Start 3 workers in the background:
```bash
$ queuectl worker start --count 3
Started 3 worker(s) in the background with PIDs: [12345, 12346, 12347]

### Configuration

Config values are stored in a SQLite table and loaded at runtime. Supported keys:

| Key          | Default | Description                                  |
|--------------|---------|----------------------------------------------|
| max_retries  | 3       | Max attempts before job moves to DLQ         |
| backoff_base | 2       | Base seconds for exponential retry backoff   |

Hyphenated and underscored forms are interchangeable. Examples:

```bash
queuectl config set max_retries 5
queuectl config set max-retries 5    # same effect
queuectl config set backoff-base 4   # becomes backoff_base internally
queuectl config get max_retries
queuectl config list
```

Internally, keys are normalized to lowercase with hyphens converted to underscores. Legacy hyphenated entries are migrated transparently the next time they are read.

---

## Testing

This project uses pytest for tests.

- Runtime dependencies: `requirements.txt`
- Dev/test dependencies: `requirements-dev.txt`

How to run tests:

1. Install dev deps (optional if you already have pytest installed):
    - pip install -r requirements-dev.txt
2. Run the suite:
    - pytest -q

Notes:
- The tests use the `queuectl` CLI; ensure the package is installed in your environment (e.g., `pip install -e .`).
- Some integration tests start background workers; they may take a few seconds to complete.