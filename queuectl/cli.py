# queuectl/cli.py
import json
import click
from .storage import Storage
from .worker import start_workers, stop_workers
from .config import load, set_kv

@click.group()
def cli():
    """queuectl — minimal job queue CLI"""
    pass

@cli.command()
@click.argument("job_json")
def enqueue(job_json):
    """Enqueue a job from JSON string.

    Example:
      queuectl enqueue '{"id":"job1","command":"echo hi","max_retries":2}'
    """
    job = json.loads(job_json)
    cfg = load()
    db = Storage(cfg["db_path"])
    if "max_retries" not in job:
        job["max_retries"] = cfg["default_max_retries"]
    ok = db.enqueue(job)
    if ok:
        click.echo(f"Enqueued {job['id']}")
    else:
        click.echo("Job id already exists", err=True)

@cli.group()
def worker():
    """Manage workers"""
    pass

@worker.command("start")
@click.option("--count", default=1, type=int, help="Number of workers")
@click.option("--background/--foreground", default=False, help="Run workers in background (records PIDs)")
def worker_start(count, background):
    cfg = load()
    procs = start_workers(count, cfg["db_path"], cfg["backoff_base"], cfg["worker_poll_interval"], background)
    if background:
        click.echo(f"Started {len(procs)} workers in background. PIDs recorded in data/workers.pids")
    else:
        pids = ", ".join(str(p.pid) for p in procs)
        click.echo(f"Started {len(procs)} workers (foreground). PID(s): {pids}\nCtrl+C to stop (graceful)")

@worker.command("stop")
def worker_stop():
    """Stop background workers using recorded PIDs"""
    killed = stop_workers()
    if not killed:
        click.echo("No worker PIDs found or already stopped.")
    else:
        click.echo(f"Sent SIGTERM to PIDs: {killed}")

@cli.command()
def status():
    """Show counts of jobs by state"""
    cfg = load()
    db = Storage(cfg["db_path"])
    stats = db.get_stats()
    click.echo("Job counts by state:")
    for s in ["pending", "processing", "completed", "failed", "dead"]:
        click.echo(f"  {s}: {stats.get(s, 0)}")

@cli.command(name="list")
@click.option("--state", default=None, help="Filter by state")
def list_cmd(state):
    """List jobs (optionally filter by state)"""
    cfg = load()
    db = Storage(cfg["db_path"])
    rows = db.list_jobs(state)
    for r in rows:
        click.echo(json.dumps(r))

@cli.group()
def dlq():
    """Dead Letter Queue ops"""
    pass

@dlq.command("list")
def dlq_list():
    cfg = load()
    db = Storage(cfg["db_path"])
    rows = db.list_jobs("dead")
    for r in rows:
        click.echo(json.dumps(r))

@dlq.command("retry")
@click.argument("job_id")
def dlq_retry(job_id):
    cfg = load()
    db = Storage(cfg["db_path"])
    db.set_pending_from_dead(job_id)
    click.echo(f"Moved {job_id} back to pending.")

@cli.group()
def config():
    """Manage config values"""
    pass

@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    # attempt int conversion
    try:
        val = int(value)
    except ValueError:
        val = value
    cfg = set_kv(key, val)
    click.echo(f"Config updated: {key} = {cfg[key]}")

if __name__ == "__main__":
    cli()
