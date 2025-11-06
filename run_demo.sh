#!/usr/bin/env bash
set -euo pipefail

python -m queuectl.cli enqueue '{"id":"ok1","command":"echo ok1","max_retries":2}'
python -m queuectl.cli enqueue '{"id":"fail1","command":"bash -c \"exit 2\"","max_retries":2}'
python -m queuectl.cli worker start --count 2 --background
sleep 2
python -m queuectl.cli status
sleep 6
python -m queuectl.cli status
python -m queuectl.cli dlq list
python -m queuectl.cli worker stop
