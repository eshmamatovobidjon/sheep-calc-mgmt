# Phase 15 - Server Deployment

| | |
|---|---|
| Status | Deferred (owner decision 2026-10-31: no server deployment for now) |
| Depends on | 14 for the full app; can run after 12 for an early Release A |
| Unblocks | Real use |
| Read first | [Roadmap](../mini-app-plan.md), [target architecture](../mini-app-architecture.md) section 11 |

## Goal

Bot, API/Mini App and PostgreSQL run on one server with HTTPS and daily backups. Real data starts fresh in PostgreSQL; there is no SQLite migration. This phase also covers the deployment and walkthrough work left from Phase 07.

## Tasks

1. Rent a small VPS (owner approval needed) and point a domain or subdomain at it. Install Docker.
2. Dockerfile: build the frontend in a Node stage, copy `web/dist` into the Python image, run as a non-root user.
3. Compose: `postgres` (named volume, no published port), `migrate`, `bot`, `api`, and `caddy` (automatic HTTPS, proxies to `api`). `restart: unless-stopped` and Docker log rotation (`max-size`).
4. `.env` on the server only. Set `MINI_APP_URL` to the HTTPS address so the bot's menu button opens the app.
5. Backups: a daily cron job runs `pg_dump` and archives `storage/uploads`, copies both off the server (another machine or cloud storage), and keeps about 14 days. Restore the latest backup once into a fresh database and check that balances match.
6. Start empty: the admin is seeded; staff press /start and are approved. Optionally run `load_demo.py` for a demo, then `--reset` before real use.
7. README: deploy, update (`git pull` + `docker compose up -d --build`), view logs, back up and restore, plus a short demo walkthrough with fictional data.

## Done When

- [ ] Following the README on a clean server brings everything up with HTTPS.
- [ ] The Mini App opens from the bot's menu button on a phone.
- [ ] A backup has been restored successfully once.
- [ ] Data survives `docker compose down` / `up` and a server reboot.
- [ ] Status columns and architecture describe the deployed setup.

## Handoff

Record the server, domain, deployment date, backup location and schedule, and the restore test result. Keep secrets out of the repository.