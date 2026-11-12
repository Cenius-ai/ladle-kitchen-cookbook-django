#!/usr/bin/env bash
# Ladle Kitchen Cookbook — install dependencies, migrate, seed, then EXIT.
# Run as an unprivileged user: everything here is project-local.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> Installing Python dependencies"
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
"$PYTHON_BIN" -m pip install -r requirements.txt

if [ ! -f .env ]; then
  echo "==> Writing .env with a generated SECRET_KEY"
  SECRET="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_hex(32))')"
  printf 'SECRET_KEY=%s\nDJANGO_DEBUG=true\n' "$SECRET" > .env
  chmod 600 .env 2>/dev/null || true
fi

echo "==> Applying migrations"
"$PYTHON_BIN" manage.py migrate --noinput

echo "==> Seeding the demo household"
"$PYTHON_BIN" manage.py seed

echo "==> Checking the project imports cleanly"
"$PYTHON_BIN" manage.py check

echo ""
echo "Install complete. Start Ladle with:"
echo "  python3 manage.py runserver 0.0.0.0:8000"
