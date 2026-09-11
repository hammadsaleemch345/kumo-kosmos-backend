# Silk & Sin — Kumo Kosmos Backend

Backend build for Kumo Kosmos, an adult fiction subscription site migrating off
Substack. Paid client project on Upwork. `silk-and-sin-prototype.html` is the
frontend, originally a click-through behavior spec, now wired to this real
backend for auth, story reading, bookmarks/favorites, admin post editing, and
static content pages.

**For the full picture — scope, decisions, what's done, what's blocked, and
why — read `context.md` first.** It's the living source of truth for this
project and is kept current after every session. This README is just quick
orientation for running the thing.

## Live site

- Frontend: <https://kumokosmos.com>
- API: <https://api.kumokosmos.com>
- Both served over real HTTPS (Let's Encrypt via Caddy) from a DigitalOcean
  droplet. See `infra/README.md` for the full deploy process.

## Stack

Python, FastAPI, PostgreSQL (SQLAlchemy + Alembic). Not specified by the
client, our own technical choice, documented in `context.md`.

## Running locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill in DATABASE_URL / SECRET_KEY

alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
cd backend
pytest tests/ -v
```

## Deploying

See `infra/README.md` for the full Terraform + Docker Compose + Caddy deploy
sequence against DigitalOcean.

## Repo layout

- `backend/` — the FastAPI app, tests, Dockerfile, Alembic migrations
- `infra/` — Terraform for the DigitalOcean droplet, firewall, container
  registry
- `silk-and-sin-prototype.html` — the frontend, wired to the backend above
- `context.md` — full project context, decisions, and status (read this)
- `feature-checklist.md` — what's real vs. mocked in the frontend prototype
- `SOW_Silk_and_Sin.docx` — the signed scope of work

## Not in this repo

The raw Substack export (`posts.csv`, `email_list.kumokosmos.csv`, `posts/`)
is excluded on purpose — it contains real subscriber emails and the client's
paid content, and this repo is public. See `.gitignore`.
