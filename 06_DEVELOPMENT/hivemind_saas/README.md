# Everlight Hive Mind SaaS

Run `./install_hive.sh` from this directory. It will:

- create a local backend `.env` with generated secrets
- provision a local SQLite runtime database
- create/update a Python virtualenv and install backend dependencies
- start `BlinkoLite` if the local controller exists
- register the `blinko-memory` Codex MCP server automatically

After install:

- Start the API with `cd backend && ../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000`
- Start the dashboard with `cd dashboard && npm install && npm run dev`
- Fetch the bootstrap token from `GET /api/bootstrap`

The backend now supports real signup/login, tenant records, encrypted integrations, stored sessions, mindmaps, usage reporting, and Stripe/manual billing fallback.
