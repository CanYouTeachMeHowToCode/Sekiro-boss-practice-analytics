#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 server (deploy/README.md): Docker, the repository in /srv/sekiro/app, a .env
# with random secrets, and the daily database backup.
#
#   SITE_ADDRESS=1-2-3-4.sslip.io BRANCH=dev bash setup.sh
set -euo pipefail

REPO_URL=${REPO_URL:-https://github.com/CanYouTeachMeHowToCode/Sekiro-boss-practice-analytics.git}
BRANCH=${BRANCH:-dev}
ROOT=/srv/sekiro
APP=$ROOT/app
CADDY_IMAGE=caddy:2.11.7    # the version deploy/compose.server.yml runs

: "${SITE_ADDRESS:?set SITE_ADDRESS, e.g. SITE_ADDRESS=1-2-3-4.sslip.io}"

# Docker Engine and the Compose plugin, from Docker's apt repository
if ! command -v docker >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl git
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
sudo usermod -aG docker "$USER"
# container logs rotate instead of filling the disk
if [ ! -f /etc/docker/daemon.json ]; then
    echo '{"log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}}' \
        | sudo tee /etc/docker/daemon.json >/dev/null
    sudo systemctl restart docker
fi
# security updates install themselves
sudo apt-get install -y unattended-upgrades

sudo mkdir -p "$ROOT"
sudo chown "$USER:" "$ROOT"
mkdir -p "$ROOT/analysis-data" "$ROOT/backups"
[ -d "$APP/.git" ] || git clone --branch "$BRANCH" "$REPO_URL" "$APP"

# The .env, written once: a random database password, and a random shared password for the testers, of which the
# .env keeps only the hash. The password itself is in site-password.txt, readable by this user only.
if [ ! -f "$APP/.env" ]; then
    password=$(openssl rand -base64 18 | tr -d '/+=')
    hash=$(sudo docker run --rm "$CADDY_IMAGE" caddy hash-password --plaintext "$password")
    (
        umask 077
        cat > "$APP/.env" <<EOF
COMPOSE_FILE=docker-compose.yml:deploy/compose.server.yml
COMPOSE_PROJECT_NAME=sekiro
POSTGRES_PASSWORD=$(openssl rand -hex 24)
ANALYSIS_DATA=$ROOT/analysis-data
SITE_ADDRESS=$SITE_ADDRESS
SITE_USER=tester
SITE_PASSWORD_HASH='$hash'
EOF
        printf '%s\n' "$password" > "$ROOT/site-password.txt"
    )
    echo "The testers' user name is tester; the shared password is in $ROOT/site-password.txt."
fi

# the daily database backup, at 08:15 UTC
backup="$APP/deploy/backup.sh >> $ROOT/backups/backup.log 2>&1"
( crontab -l 2>/dev/null | grep -vF "$APP/deploy/backup.sh" || true; echo "15 8 * * * $backup" ) | crontab -

echo "Done. Next: upload the analysis data folder to $ROOT/analysis-data, log in again (for the docker group),"
echo "then run $APP/deploy/deploy.sh"
