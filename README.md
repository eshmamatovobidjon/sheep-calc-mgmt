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

## Template and demo files

The trip template is defined in `src/sheepbot/excel/template_spec.py`. The bot builds it on the fly for `/template`; the files in `assets/` are generated copies.

```bash
python scripts/build_template.py      # -> assets/templates/trip_template_v1.xlsx
python scripts/build_demo_files.py    # -> assets/demo/demo_trip_101.xlsx, demo_trip_102.xlsx
```

Demo data is fictional and deterministic (fixed seed). Regenerate both after changing the spec.

## License

TBD
