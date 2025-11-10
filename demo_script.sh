set -e

echo "--- QueueCTL Demo Script ---"
echo ""
echo ""
echo "*********************************************************"
echo "[1/7] Cleaning up old database and workers..."
echo "*********************************************************"
echo ""
queuectl worker stop > /dev/null 2>&1 || true
rm -f ~/.queuectl/queue.db || true
rm -f ~/.queuectl/queuectl.pid || true

echo "Initializing new database..."
queuectl init-db

echo ""
echo "*********************************************************"
echo "[2/7] Configuring settings..."
echo "*********************************************************"
echo ""

queuectl config set max_retries 2
queuectl config set backoff_base 1
queuectl config list

echo ""
echo "*********************************************************"
echo "[3/7] Starting workers..."
echo "*********************************************************"
echo ""

queuectl worker start --count 2
sleep 1
queuectl status

echo ""
echo "*********************************************************"
echo "[4/7] Testing enqueue of successful job ..."
echo "*********************************************************"
echo ""

queuectl enqueue "{\"id\": \"job_success\", \"command\": \"echo 'Job Succeeded'\"}"
sleep 2
queuectl list --state completed | grep "job_success" >/dev/null && echo "Success test passed."

echo ""
echo "*********************************************************"
echo "[5/7] Testing enqueue of failed job, retry, and DLQ ..."
echo "*********************************************************"
echo ""

queuectl enqueue '{"id": "job_fail", "command": "exit 1"}'
echo "Waiting for job to fail and move to DLQ (approx 3-4s)..."
sleep 4
queuectl dlq list | grep "job_fail" | grep "2/2" >/dev/null && echo "DLQ test passed."

echo "Testing DLQ retry..."
queuectl dlq retry job_fail
sleep 0.5
queuectl list --state pending | grep "job_fail" | grep "0/2" >/dev/null && echo "DLQ retry passed."

echo ""
echo "*********************************************************"
echo "[6/7] Testing job persistence across restarts..."
echo "*********************************************************"
echo ""

queuectl worker stop
sleep 1
queuectl enqueue "{\"id\": \"job_persist\", \"command\": \"echo 'Persistence OK'\"}"
queuectl worker start --count 1
sleep 3
queuectl list --state completed | grep "job_persist" >/dev/null && echo "Persistence test passed."

echo ""
echo "*********************************************************"
echo "[7/7] Testing multi-worker processing..."
echo "*********************************************************"
echo ""

queuectl worker stop > /dev/null
queuectl worker start --count 3
sleep 1
echo "Enqueuing 3 jobs that take 2 seconds each..."
queuectl enqueue '{"id": "multi_1", "command": "sleep 2"}'
queuectl enqueue '{"id": "multi_2", "command": "sleep 2"}'
queuectl enqueue '{"id": "multi_3", "command": "sleep 2"}'
sleep 3
COMPLETED_COUNT=$(queuectl list --state completed | grep "multi_" | wc -l)
if [ "$COMPLETED_COUNT" -eq 3 ]; then
  echo "Multi-worker test passed."
else
  echo "ERROR: Not all multi-worker jobs completed. Found $COMPLETED_COUNT."
fi

echo "--- DEMO COMPLETE ---"
queuectl worker stop || true
