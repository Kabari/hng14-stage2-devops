import redis
import time
import os
import signal
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

running = True

def shutdown(signum, frame):
    global running
    logger.info("Received shutdown signal, stopping worker...")
    running = False

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

def process_job(job_id):
    print(f"Processing job {job_id}")
    time.sleep(2)  # simulate work
    r.hset(f"job:{job_id}", "status", "completed")
    print(f"Done: {job_id}")

while running:
    try:
        job = r.brpop("jobs", timeout=5)
        if job:
            _, job_id = job
            process_job(job_id.decode())
    except redis.exceptions.ConnectionError as exc:
        logger.error(f"Redis connection error: {exc}. Retrying in 5s...")
        time.sleep(5)  # wait before retrying