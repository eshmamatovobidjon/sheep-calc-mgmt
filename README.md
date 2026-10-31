# sheep-calc-mgmt

Telegram bot for a sheep-meat trading business: trip uploads from an Excel template, client payments and reports (PDF/XLSX). See [AGENTS.md](AGENTS.md) and [docs/](docs/).

## Next delivery track: Telegram Mini App

The [Mini App and PostgreSQL roadmap](docs/mini-app-plan.md) defines phases 08-15: PostgreSQL, an authenticated API, client/payment screens, reports and user admin, trip entry and editing in the app, and server deployment. It is sized for a small team. The [target architecture](docs/mini-app-architecture.md) records the implementation contracts.

Phases 08-12 are done (PostgreSQL, API with Telegram login, Mini App with clients, payments, trips, reports and user admin); trip entry in the app (13-14) and server deployment (15) are planned. Next is [Phase 13](docs/phases/phase-13-trip-workspace.md).

## Run locally

Requires Python 3.12+ and Docker (for PostgreSQL).

```bash
git clone https://github.com/eshmamatovobidjon/sheep-calc-mgmt.git
cd sheep-calc-mgmt
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # set BOT_TOKEN, ADMIN_TELEGRAM_ID and a POSTGRES_PASSWORD (also in DATABASE_URL)
docker compose up -d postgres   # PostgreSQL 17 on 127.0.0.1:5432
alembic upgrade head            # create/upgrade the schema
python -m sheepbot
```

Uploads are stored in `./storage/uploads/`. Don't run the bot locally while the Docker `bot` service is polling with the same token.

## Run with Docker

```bash
cp .env.example .env            # as above
docker compose up -d --build    # postgres -> migrate (alembic upgrade head) -> bot + api
docker compose logs -f bot
```

PostgreSQL data lives in the `postgres_data` volume; uploads in `./storage/` on the host.

## API

The Mini App API runs as a separate process on `127.0.0.1:8000` (`api` service in Docker, or `python -m sheepbot.api` locally). Every request needs `Authorization: tma <Telegram.WebApp.initData>`; see [architecture section 9a](docs/architecture.md). OpenAPI docs: <http://127.0.0.1:8000/api/docs>.

For local frontend work without Telegram, set `APP_ENV=dev` and `DEV_AUTH_TELEGRAM_ID=<your id>` when running the API locally; requests without initData then act as that user. Never set these on a server.

## Mini App (frontend)

The app lives in `web/` (Vite + React + TypeScript; needs Node 20.19+). The Docker image builds it and the API serves it at <http://127.0.0.1:8000/>; outside Telegram it only shows "open from the bot".

```bash
cd web && npm ci
# terminal 1 (project root): API with the dev login on port 8001
APP_ENV=dev DEV_AUTH_TELEGRAM_ID=<your id> API_PORT=8001 python -m sheepbot.api
# terminal 2 (web/): dev server on http://localhost:5173 proxying /api
API_URL=http://127.0.0.1:8001 npm run dev
npm run lint && npm run typecheck && npm run build
```

To open it inside Telegram, Telegram needs an HTTPS URL: expose port 8000 with a tunnel (e.g. `cloudflared tunnel --url http://127.0.0.1:8000`), put the URL into `MINI_APP_URL` and restart the bot; the chat menu button "Приложение" then opens the app. Use a separate development bot if the main bot is in use.

## Demo data

```bash
python scripts/load_demo.py             # trips 101/102 + fictional payments; refuses if trips exist
python scripts/load_demo.py --reset     # empty trips/clients/uploads/payments first (asks to confirm)
```

## Schema changes

```bash
alembic revision --autogenerate -m "what changed"   # then review the generated file
alembic upgrade head
alembic check                                       # models and migrations agree
```

## Template and demo files

The trip template is defined in `src/sheepbot/excel/template_spec.py`. The bot builds it on the fly for `/template`; the files in `assets/` are generated copies.

```bash
python scripts/build_template.py      # -> assets/templates/trip_template_v1.xlsx
python scripts/build_demo_files.py    # -> assets/demo/demo_trip_101.xlsx, demo_trip_102.xlsx
```

Demo data is fictional and deterministic (fixed seed). Regenerate both after changing the spec.

## License

TBD
