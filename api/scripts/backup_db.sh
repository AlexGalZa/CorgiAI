#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/backups}"
mkdir -p "$BACKUP_DIR"
pg_dump -h "${DATABASE_HOST:-localhost}" -U "${DATABASE_USER:-corgi_admin}" -d "${DATABASE_NAME:-corgi}" | gzip > "$BACKUP_DIR/corgi_$TIMESTAMP.sql.gz"
# Keep only last 30 days
find "$BACKUP_DIR" -name "corgi_*.sql.gz" -mtime +30 -delete
echo "Backup complete: corgi_$TIMESTAMP.sql.gz"
