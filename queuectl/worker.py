# queuectl/worker.py
import multiprocessing as mp
import os
import signal
import time
from .storage import Storage, iso_now
from .executor import run_command

SHUTDOWN = mp.Event()
PIDS_FILE = "data/workers.pids"

def _install_signal_handlers():
    def _sigterm(_signum, _frame):
        SHUTDOWN.set()
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

def worker_loop(db_path: str, backoff_base: int, poll_interval: int):
    _install_signal_handlers()
    storage = Storage(db_path)
    while not SHUTDOWN.is_set():
        now = iso_now()
        job = storage.claim_job(now)
        if not job:
            time.sleep(poll_interval)
            continue

        job_id = job["id"]
        command = job["command"]
        attempts = int(job["attempts"]) + 0
        max_retries = int(job["max_retries"]) if job["max_retries"] is not None else 3
        timeout = job.get("timeout_seconds")

        code, output = run_command(command, timeout=timeout)
        if code == 0:
            storage.set_job_completed(job_id)
        else:
            attempts += 1
            storage.set_job_failed(job_id, attempts, max_retries, backoff_base, output)

def start_workers(count: int, db_path: str, backoff_base: int, poll_interval: int, background: bool):
    os.makedirs(os.path.dirname(PIDS_FILE) or ".", exist_ok=True)
    procs = []
    for _ in range(count):
        p = mp.Process(target=worker_loop, args=(db_path, backoff_base, poll_interval), daemon=False)
        p.start()
        procs.append(p)
    # record PIDs
    with open(PIDS_FILE, "a") as f:
        for p in procs:
            f.write(str(p.pid) + "\n")
    if background:
        # In background mode, return immediately (PIDs recorded)
        return procs
    # Foreground: block until interrupted
    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        pass
    return procs

def stop_workers():
    if not os.path.exists(PIDS_FILE):
        return []
    with open(PIDS_FILE) as f:
        pids = [int(x.strip()) for x in f.readlines() if x.strip()]
    alive = []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            alive.append(pid)
        except ProcessLookupError:
            # already gone
            continue
        except Exception:
            continue
    # cleanup pid file
    try:
        os.remove(PIDS_FILE)
    except OSError:
        pass
    return alive
