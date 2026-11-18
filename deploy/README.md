# deploy: the private test server

The app on one x86_64 Linux server with Docker Compose, for the V4 M4 private test (plan, in Chinese: `plan_m4.md`).
`compose.server.yml` adds Caddy in front of `docker-compose.yml`: HTTPS with a certificate it gets by itself, and a
shared password for the whole site, so only invited testers reach the app. Nothing else is reachable from outside.

| File | Use |
|---|---|
| `compose.server.yml` | the server's additions to `docker-compose.yml` |
| `Caddyfile` | HTTPS, the shared password, the proxy to the frontend |
| `env.server.example` | the shape of the server's `.env` (`setup.sh` writes the real one) |
| `setup.sh` | once, on a fresh Ubuntu 24.04 server: Docker, the repository, `.env`, the daily backup |
| `deploy.sh` | every update: pull, build, restart, check |
| `backup.sh` | the daily database dump (cron), the last 7 kept |

Never commit the server's `.env`, its IP, the project ID or any password: the repository is public.

## 1. The server (Google Cloud)

With the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) logged in (`gcloud init`) on the project:

```bash
REGION=us-east1
ZONE=us-east1-b      # another zone of the region if this one has no capacity
gcloud services enable compute.googleapis.com
gcloud compute addresses create sekiro-test --region=$REGION
gcloud compute instances create sekiro-test --zone=$ZONE --machine-type=e2-standard-4 \
    --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
    --boot-disk-size=100GB --boot-disk-type=pd-balanced \
    --address=sekiro-test --tags=web
gcloud compute firewall-rules create sekiro-web --allow=tcp:80,tcp:443 --target-tags=web
```

SSH (port 22) is open through the default network's `default-allow-ssh` rule; `gcloud compute ssh` manages the keys.
Without a domain, the site's address is the static IP with dashes on sslip.io:

```bash
IP=$(gcloud compute addresses describe sekiro-test --region=$REGION --format='value(address)')
SITE_ADDRESS=${IP//./-}.sslip.io
```

## 2. Set up

```bash
gcloud compute scp deploy/setup.sh sekiro-test:~ --zone=$ZONE
gcloud compute ssh sekiro-test --zone=$ZONE --command "SITE_ADDRESS=$SITE_ADDRESS BRANCH=dev bash setup.sh"
```

`BRANCH` is the branch the server runs. The testers' user name is `tester`; the shared password is in
`/srv/sekiro/site-password.txt` on the server.

Upload the analysis data folder (`analysis/README.md`, about 500 MB) from the computer that has it:

```bash
gcloud compute scp --recurse <folder>/* sekiro-test:/srv/sekiro/analysis-data/ --zone=$ZONE
```

## 3. Deploy and check

```bash
gcloud compute ssh sekiro-test --zone=$ZONE --command "/srv/sekiro/app/deploy/deploy.sh"
```

The first run builds every image (15–20 minutes). It ends with the worker's decode check, its `pipeline:` line
(`v2 on cpu` when it will analyse) and the site's HTTPS status (401 without the password). Before giving the address
to testers, also check by hand:

- an uploaded test recording gives exactly the research tools' report (`plan_m4.md`, step 1.6);
- an unrelated video is rejected;
- two accounts do not see each other's recordings;
- after `sudo reboot`, recordings, reports and clips are still there.

## Updates

```bash
gcloud compute ssh sekiro-test --zone=$ZONE --command "/srv/sekiro/app/deploy/deploy.sh"
```

It pulls the branch and rebuilds what changed: 2–3 minutes for code, 5–10 for the worker's dependencies, with
10–30 seconds of downtime. It refuses while recordings wait or are being analysed (`--force` overrides). After a new
version of the analysis data, upload the folder again and run `docker compose restart worker` in `/srv/sekiro/app`.

## Backups

`backup.sh` dumps the database every day at 08:15 UTC into `/srv/sekiro/backups` and keeps 7 dumps. Videos and clips
are not in it. To restore a dump into an empty database:

```bash
gunzip -c /srv/sekiro/backups/sekiro-<date>.sql.gz | docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## End of the test

Testers' recordings are all deleted when the test ends (`plan_m4.md`). If the server is not kept:

```bash
gcloud compute instances delete sekiro-test --zone=$ZONE
gcloud compute addresses delete sekiro-test --region=$REGION
gcloud compute firewall-rules delete sekiro-web
```

## Trying the server setup locally

Its own Compose project and ports, so the local stack and database are untouched. Caddy serves `localhost` with its
own local certificate (`curl -k`):

```bash
docker compose -p sekiro-deploy-check --env-file <env file> -f docker-compose.yml -f deploy/compose.server.yml up -d --build
```

with `HTTP_PORT` and `HTTPS_PORT` set to free ports and `SITE_ADDRESS=localhost` in the env file.
