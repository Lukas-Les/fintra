#!/bin/bash
set -e

echo "debug mode"
echo "installing debugpy..."
cd /app/
uv sync --group debug

# Run with debugger
echo "Starting application with debugger on 0.0.0.0:5678"
ls
exec .venv/bin/python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m fintra "$@"
