#!/usr/bin/env python3
# demo/prepare_demo.py
import json, subprocess, sys, os
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
CLI = [sys.executable, "-m", "queuectl.cli"]

def run_cli(args):
    return subprocess.run(CLI + args, capture_output=True, text=True)

def enqueue(obj):
    s = json.dumps(obj)
    r = run_cli(["enqueue", s])
    print(r.stdout.strip() or r.stderr.strip())

def list_state(state=None):
    args = ["list"]
    if state:
        args += ["--state", state]
    r = run_cli(args)
    print(r.stdout.strip())

def main():
    print("Preparing demo jobs (will show pending snapshot)...\n")

    # 1) pending-only job (we won't start workers yet)
    enqueue({"id":"demo_pending","command":"echo pending_demo","max_retries":2})

    # 2) long-running job (for showing processing)
    # make it long enough to manually observe processing
    enqueue({"id":"demo_processing","command":"sleep 10","max_retries":2})

    # 3) successful job
    enqueue({"id":"demo_completed","command":"echo completed_demo","max_retries":2})

    # 4) failing job that will demonstrate retries -> DLQ later
    enqueue({"id":"demo_fail","command":"bash -c \"exit 1\"","max_retries":2})

    # 5) another simple job
    enqueue({"id":"demo_ok2","command":"echo ok2","max_retries":2})

    print("\n--- Pending snapshot (before workers) ---")
    list_state("pending")
    print("\nNow follow the instructions in README/demo steps to run workers and capture processing/completed/dead states.")

if __name__ == "__main__":
    main()
