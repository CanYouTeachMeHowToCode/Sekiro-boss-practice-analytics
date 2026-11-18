#!/usr/bin/env bash
# Dumps the database, keeping the last 7 dumps (cron, set up by deploy/setup.sh). The videos and clips are not in it:
# they stay in the recordings volume.
set -euo pipefail
cd "$(dirname "$0")/.."

dir=/srv/sekiro/backups
out="$dir/sekiro-$(date -u +%F).sql.gz"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$out.tmp"
mv "$out.tmp" "$out"
ls -1t "$dir"/sekiro-*.sql.gz | tail -n +8 | xargs -r rm --
echo "$(date -u +%FT%TZ) $out"
