#!/bin/sh
# Fly's fly.toml had a dedicated release_command for migrations; a plain Droplet has no
# equivalent, so this runs the migration before every start instead. alembic upgrade head
# is a no-op once the DB is already current, so it's safe to run on every container restart.
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
