#!/bin/bash
set -e

echo "debug mode"
echo "installing debugpy..."

/app/.venv/bin/pip install debugpy

# Run with debugger
echo "Starting application with debugger on 0.0.0.0:5678"
exec python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m fintra "$@"
