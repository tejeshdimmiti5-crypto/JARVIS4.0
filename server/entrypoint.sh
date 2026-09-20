#!/bin/sh
set -eu

if [ "${ENVIRONMENT:-development}" = "production" ]; then
  : "${JWT_SECRET:?JWT_SECRET must be set in production}"
  if [ "${#JWT_SECRET}" -lt 32 ]; then
    echo "JWT_SECRET must be at least 32 characters in production" >&2
    exit 1
  fi
fi

echo "JARVIS: applying database migrations..."
alembic upgrade head

exec "$@"
