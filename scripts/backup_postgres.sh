#!/usr/bin/env bash
# Automatic logical backup for Bhudi Postgres.
# Usage: ./scripts/backup_postgres.sh [output_dir]
set -euo pipefail

OUT_DIR="${1:-./backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="${OUT_DIR}/bhudi_${STAMP}.sql.gz"

mkdir -p "${OUT_DIR}"

: "${PGHOST:=127.0.0.1}"
: "${PGPORT:=5432}"
: "${PGUSER:=bhudi}"
: "${PGDATABASE:=bhudi}"

echo "Backing up ${PGDATABASE}@${PGHOST}:${PGPORT} → ${FILE}"
pg_dump --no-owner --format=plain | gzip -c > "${FILE}"
echo "OK $(du -h "${FILE}" | awk '{print $1}')"

# Retain last 14 daily dumps
ls -1t "${OUT_DIR}"/bhudi_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
