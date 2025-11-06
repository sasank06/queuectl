# queuectl/config.py
import json, os

DEFAULT = {
  "db_path": "data/jobs.db",
  "backoff_base": 2,
  "default_max_retries": 3,
  "worker_poll_interval": 1
}
CONFIG_FILE = "config.json"


def load():
    cfg = DEFAULT.copy()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            filecfg = json.load(f)
            cfg.update(filecfg)
    os.makedirs(os.path.dirname(cfg["db_path"]) or ".", exist_ok=True)
    return cfg

def set_kv(k, v):
    cfg = load()
    cfg[k] = v
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg
