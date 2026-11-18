#!/usr/bin/env bash
# Updates the server to the latest commit of its branch and restarts what changed (deploy/README.md). It refuses
# while recordings wait or are being analysed, since a restart would start their analysis over.
#
#   deploy/deploy.sh            update and restart
#   deploy/deploy.sh --force    even with recordings in the queue
set -euo pipefail
cd "$(dirname "$0")/.."

# only on a server checkout: its .env names deploy/compose.server.yml (deploy/setup.sh)
if ! grep -q '^COMPOSE_FILE=.*deploy/compose.server.yml' .env 2>/dev/null; then
    echo "not a server checkout: .env has no COMPOSE_FILE with deploy/compose.server.yml (deploy/setup.sh)"
    exit 1
fi
force=false
[ "${1:-}" = "--force" ] && force=true

if [ -n "$(docker compose ps --status running -q postgres)" ]; then
    busy=$(echo "select count(*) from recordings where status in ('uploaded', 'checking', 'queued', 'processing');" \
        | docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAq' 2>/dev/null || true)
    if [ -n "$busy" ] && [ "$busy" != "0" ] && ! $force; then
        echo "$busy recording(s) waiting or being analysed: deploy later, or with --force"
        exit 1
    fi
fi

git pull --ff-only
docker compose up -d --build --remove-orphans
docker image prune -f >/dev/null

# the backend applies the migrations on start
for i in $(seq 90); do
    if docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
        break
    fi
    if [ "$i" = 90 ]; then
        echo "the backend did not come up: docker compose logs backend"
        exit 1
    fi
    sleep 2
done
echo "backend: up"

# the worker analyses only when it decodes video exactly as the research did (analysis/README.md)
docker compose exec -T worker python -m sekiro_analysis.decode
sleep 5
docker compose logs worker | grep "pipeline:" | tail -1

# HTTPS through Caddy (the first start may still be getting the certificate)
site=$(grep '^SITE_ADDRESS=' .env | cut -d= -f2)
code=$(curl -s -o /dev/null -w '%{http_code}' "https://$site/" || true)
echo "https://$site/: $code (401 expected without the shared password)"
git log --oneline -1
