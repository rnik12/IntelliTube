#!/usr/bin/env bash
set -euo pipefail

# Root directory (default to current dir)
ROOT="${1:-.}"

echo "Cleaning Python bytecode and cache in $ROOT …"

# Delete __pycache__ directories
find "$ROOT" -type d -name "__pycache__" -prune -exec rm -rf {} +

# Delete compiled Python files
find "$ROOT" -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.py[co]" \) -delete

# Optionally, delete other tool caches:
find "$ROOT" -type d \( -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".cache" \) -prune -exec rm -rf {} +

echo "Done."
