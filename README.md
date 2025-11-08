This is a job-queue you can run locally to enqueue shell commands, run workers (multiple), automatically retry failures with exponential backoff, and move permanently failed jobs to a Dead Letter Queue (DLQ). Everything is controlled from the CLI.

What this repo contains:

queuectl/ — core package (CLI, worker, storage, executor, config)
data/ — runtime data (jobs.db, workers.pids)
config.json — runtime configuration
requirements.txt — dependencies (click)
tests/test_scenarios.py — automated scenario tests
demo/prepare_demo.py, demo/validate_demo.py — demo helpers

QUEUECL stores jobs in SQLite, workers claim and execute them, failed jobs are retried with delay = backoff_base ** attempts, and after max_retries a job is moved to the DLQ.





Insallation & setup:

1. Clone repo and change to repo root.
2. Create and activate virtualenv (follow these commands):
            python -m venv venv
            source .venv/bin/activate    # Git Bash / WSL
        on Windows PowerShell:
            .\venv\Scripts\Activate.ps1

    pip install -r requirements.txt

3. Ensure config.json exists (repo already contains a default). If not, add it:
        {
      "db_path": "data/jobs.db",
      "backoff_base": 2,
      "default_max_retries": 3,
      "worker_poll_interval": 1
        }

4. Create data/ directory if it doesn't exist





CLI usage:

Use a POSIX shell (Git Bash) for exact quoting shown below.

1. 
Enqueue a job:
python -m queuectl.cli enqueue '{"id":"job1","command":"sleep 2","max_retries":3}'


2. 
Start workers (foreground):
python -m queuectl.cli worker start --count 3

3. 
Start workers (background):
python -m queuectl.cli worker start --count 3 --background

4. 
Stop background workers
python -m queuectl.cli worker stop

5. 
Show summary counts:
python -m queuectl.cli status

6. 
List jobs:
python -m queuectl.cli list --state pending
python -m queuectl.cli list --state completed

7. 
DLQ operations:
python -m queuectl.cli dlq list
python -m queuectl.cli dlq retry job1

8. 
Config:
python -m queuectl.cli config set backoff_base 3
python -m queuectl.cli config set default_max_retries 5






Architecture:
->  Storage: SQLite file (data/jobs.db). Jobs saved with full metadata.

-> Workers: multiprocessing.Process workers poll DB, claim job using an atomic transaction (BEGIN IMMEDIATE + SELECT + UPDATE state='processing') to avoid duplicate processing.

-> Execution: subprocess.run(shell=True) runs the command. Exit code 0 → completed, non-zero → failed path.

-> Retry: set_job_failed increments attempts. If attempts < max_retries, compute next_run_at = now + base_attempts and set state = pending. If attempts exhausted → state = dead (DLQ).

-> DLQ: jobs with "state":"dead". CLI provides dlq list and dlq retry <id>.





How to demonstrate each required test scenario manually:

1. 
Basic job completes

python -m queuectl.cli enqueue '{"id":"t1","command":"echo ok","max_retries":1}'

Start worker (foreground) in separate terminal:

python -m queuectl.cli worker start --count 1
python -m queuectl.cli list --state completed → t1 appears.

2. 
Failed job retries and then DLQ

Enqueue failing job: python -m queuectl.cli enqueue '{"id":"t2","command":"bash -c \"exit 2\"","max_retries":2}'

Start worker. Check list --state pending after first failure → attempts increments and next_run_at shows the scheduled retry.

3. 
Multiple workers, no overlap
Enqueue many jobs (j1..j10).
Start python -m queuectl.cli worker start --count 3.

python -m queuectl.cli list --state completed   
=>all jobs completed once.

4. 
Invalid commands fail gracefully
Enqueue {"id":"inv","command":"nonexistent_cmd","max_retries":1}.
Start worker → after retry it should be in DLQ with last_error showing failure.

5. 
Persistence across restart
Enqueue jobs, stop worker or exit terminal.
Restart worker: jobs are still in DB and processed.





Automated tests:
python test/prepare.py

In Terminal A:
python -m queuectl.cli worker start --count 1

In Terminal B:
python -m queuectl.cli list --state processing

Terminal A: press Ctrl+C to stop foreground worker.

In Terminal C:
python -m queuectl.cli worker start --count 1 --background

Wait ~10–20s for retries to finish, then in another terminal:
python demo/validate_demo.py


python -m queuectl.cli worker stop


The outputs are present in output_vis folder in this repo.

Checklist:

Retry & DLQ implemented | ✅ | Backoff and DLQ proven by test outputs |
No duplicate/race issues | ✅ | Multi-worker test (`--count 3`) completed all once |
Data persistent | ✅ | SQLite `data/jobs.db` retains jobs after restart |
Configurable | ✅ | Config file + `config set` CLI commands |
Clear README | ✅ 
