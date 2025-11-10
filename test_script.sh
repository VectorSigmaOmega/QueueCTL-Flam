#!/bin/bash

# test_script.sh
# Validation script for the queuectl application

echo "--- QueueCTL Test Script ---"

# --- 1. Cleanup & Setup ---
echo "[1/7] Cleaning up old database and workers..."
queuectl worker stop > /dev/null 2>&1
rm -f ~/.queuectl/queue.db
rm -f ~/.queuectl/queuectl.pid

echo "Initializing new database..."
queuectl init-db

# --- 2. Configuration Test ---
echo "[2/7] Configuring settings..."
queuectl config set max_retries 2
queuectl config set backoff_base 1 # 1s base for faster testing

# --- 3. Worker Management Test ---
echo "[3/7] Starting workers..."
queuectl worker start --count 2

# --- FIX: Wait 1 second for workers to start and write their PIDs ---
sleep 1

# Check status
queuectl status | grep "2 active worker(s)"
if [ $? -ne 0 ]; then
    echo "ERROR: Workers did not start correctly."
    echo "--- Output from 'queuectl status' ---"
    queuectl status
    echo "-------------------------------------"
    exit 1
fi
echo "Worker start test passed."

# --- 4. Basic Job Test (Success) ---
echo "[4/7] Testing successful job (Scenario 1)..."
queuectl enqueue "{\"id\": \"job_success\", \"command\": \"echo 'Job Succeeded'\"}"

sleep 2 # Give workers time to process
queuectl list --state completed | grep "job_success"
if [ $? -ne 0 ]; then
    echo "ERROR: Successful job did not complete."
    queuectl worker stop
    exit 1
fi
echo "Success test passed."

# --- 5. Failed Job & DLQ Test (Scenario 2) ---
echo "[5/7] Testing failed job, retry, and DLQ (Scenario 2)..."
queuectl enqueue '{"id": "job_fail", "command": "exit 1"}'

echo "Waiting for job to fail and move to DLQ (approx 3-4s)..."
# Backoff: 1*(2^0) = 1s, then 1*(2^1) = 2s. Total ~3s
sleep 4 

# Check if it's in the DLQ
queuectl dlq list | grep "job_fail" | grep "2/2"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed job did not move to DLQ correctly."
    queuectl worker stop
    exit 1
fi
echo "DLQ test passed."

# Test DLQ retry
echo "Testing DLQ retry..."
queuectl dlq retry job_fail
sleep 0.5 # Give time for state to change
queuectl list --state pending | grep "job_fail" | grep "0/2"
if [ $? -ne 0 ]; then
    echo "ERROR: DLQ retry did not move job to pending."
    queuectl worker stop
    exit 1
fi
echo "DLQ retry passed. (Job will now fail again and return to DLQ)"
sleep 4 # Let it fail again

# --- 6. Persistence Test (Scenario 5) ---
echo "[6/7] Testing job persistence across restarts (Scenario 5)..."
echo "Stopping workers..."
queuectl worker stop
sleep 1

echo "Enqueuing job while workers are offline..."
queuectl enqueue "{\"id\": \"job_persist\", \"command\": \"echo 'Persistence OK'\"}"

echo "Restarting workers..."
queuectl worker start --count 1
sleep 1 # Wait for worker to start

sleep 2 # Give worker time to pick up job
queuectl list --state completed | grep "job_persist"
if [ $? -ne 0 ]; then
    echo "ERROR: Job did not persist worker restart."
    queuectl worker stop
    exit 1
fi
echo "Persistence test passed."

# --- 7. Multi-Worker Test (Scenario 3) ---
echo "[7/7] Testing multi-worker processing (Scenario 3)..."
queuectl worker stop > /dev/null
queuectl worker start --count 3
sleep 1 # Wait for workers to start

echo "Enqueuing 3 jobs that take 2 seconds each..."
START_TIME=$(date +%s)
queuectl enqueue '{"id": "multi_1", "command": "sleep 2"}'
queuectl enqueue '{"id": "multi_2", "command": "sleep 2"}'
queuectl enqueue '{"id": "multi_3", "command": "sleep 2"}'

echo "Waiting for parallel completion..."
sleep 3 # All 3 jobs should finish in ~2s, 3s is a safe buffer

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# Check that 3 jobs are completed
COMPLETED_COUNT=$(queuectl list --state completed | grep "multi_" | wc -l)
if [ "$COMPLETED_COUNT" -ne 3 ]; then
    echo "ERROR: Not all multi-worker jobs completed. Expected 3, found $COMPLETED_COUNT."
    queuectl list
    queuectl worker stop
    exit 1
fi

echo "All 3 jobs completed in $ELAPSED seconds."
if [ $ELAPSED -gt 5 ]; then
    echo "ERROR: Jobs ran serially, not in parallel!"
    queuectl worker stop
    exit 1
fi
echo "Multi-worker test passed."


# --- Cleanup ---
echo "--- ALL TESTS PASSED ---"
echo "Cleaning up..."
queuectl worker stop
echo "Test complete."