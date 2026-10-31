# sheep-calc-mgmt

Telegram bot for a sheep-meat trading business: trip uploads from an Excel template, client payments and reports (PDF/XLSX). See [AGENTS.md](AGENTS.md) and [docs/](docs/).

## Run locally

Requires Python 3.12+.

```bash
git clone https://github.com/eshmamatovobidjon/sheep-calc-mgmt.git
cd sheep-calc-mgmt
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # set BOT_TOKEN and ADMIN_TELEGRAM_ID
python -m sheepbot
```

The SQLite database and uploads are stored in `./storage/` (created on startup).

## Run with Docker

```bash
cp .env.example .env            # set BOT_TOKEN and ADMIN_TELEGRAM_ID
docker compose up -d --build
docker compose logs -f bot
```

Data persists in `./storage/` on the host.

## License

TBD
