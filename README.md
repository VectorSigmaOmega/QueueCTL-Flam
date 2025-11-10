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