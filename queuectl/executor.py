# queuectl/executor.py
import subprocess
from typing import Optional, Tuple

def run_command(command: str, timeout: Optional[int] = None) -> Tuple[int, str]:
    """Run a shell command. Return (exit_code, combined_output)."""
    try:
        completed = subprocess.run(
            command,
            shell=True,              # required for assignment-style commands (echo, sleep)
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return completed.returncode, (completed.stdout or "") + (completed.stderr or "")
    except subprocess.TimeoutExpired as e:
        return 124, f"Timeout after {e.timeout}s\n{e.stdout or ''}{e.stderr or ''}"
    except Exception as e:
        return 1, str(e)
