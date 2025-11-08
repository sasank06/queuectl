#!/usr/bin/env python3
# demo/validate_demo.py
import subprocess, json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
CLI = [sys.executable, "-m", "queuectl.cli"]

def run_cli(args):
    return subprocess.run(CLI + args, capture_output=True, text=True)

def print_state(state):
    print(f"\n--- {state.upper()} ---")
    r = run_cli(["list", "--state", state])
    if r.stdout.strip():
        print(r.stdout.strip())
    else:
        print("(none)")

def print_dlq():
    print("\n--- DLQ (dead) ---")
    r = run_cli(["dlq", "list"])
    print(r.stdout.strip() or "(none)")

def main():
    print("Final job snapshots (completed / dead)\n")
    print_state("completed")
    print_dlq()
if __name__ == "__main__":
    main()
