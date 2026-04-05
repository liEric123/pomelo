#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -x "./.venv/bin/python" ]]; then
  PYTHON_BIN="./.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  PYTHON_BIN="python3"
fi

DB_INFO="$("$PYTHON_BIN" - <<'PY'
from pathlib import Path

from database import DATABASE_URL
from sqlalchemy.engine import make_url

url = make_url(DATABASE_URL)
backend = url.get_backend_name()

if backend == "sqlite":
    database = url.database or ""
    if database in ("", ":memory:"):
        print("sqlite-memory")
    else:
        path = Path(database)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        print(f"sqlite-file:{path}")
else:
    print("non-sqlite")
PY
)"

case "$DB_INFO" in
  sqlite-file:*)
    DB_PATH="${DB_INFO#sqlite-file:}"
    rm -f "$DB_PATH" "${DB_PATH}-shm" "${DB_PATH}-wal" "${DB_PATH}-journal"
    echo "Removed SQLite database at $DB_PATH"
    ;;
  *)
    "$PYTHON_BIN" seed.py --reset-only
    ;;
esac
