# AGENTS.md

## Cursor Cloud specific instructions

### Overview

GlobalDesignerHub.com is a Django 5.2 fashion designer portfolio / tech pack platform. The single Django project (`gdh/`) hosts three apps: `designer_portfolio` (core), `sitebuilder`, and `marketing`, plus an `ai_chat` module. There is also a React Native (Expo) mobile app under `mobile/`, but it is optional and not required for backend development.

### Running the app

See `README.md` for full details. Quick reference:

```
python3 manage.py runserver 8004
```

The `.env` file must contain at minimum `DEBUG=True` and `DATABASE_URL=sqlite:///db.sqlite3` for local dev (SQLite). The settings file (`gdh/settings.py`) will raise a `RuntimeError` if no database configuration is found and you are not running tests.

### Database

- **Tests** always use in-memory SQLite (hardcoded in settings when `test` is in `sys.argv`).
- **Dev server** uses whatever `DATABASE_URL` points to. `sqlite:///db.sqlite3` is simplest for local work.
- After changing `DATABASE_URL` or pulling new migrations, run `python3 manage.py migrate`.

### Tests

```
python3 manage.py test
```

All 47 tests run against in-memory SQLite — no external services needed. No `.env` is required for tests because the settings use in-memory SQLite when `test` is in `sys.argv`.

### Linting

No project-specific linter config exists. You can use `ruff` (installed in the environment):

```
ruff check --select=E,F,I --ignore=E501 gdh/ designer_portfolio/ marketing/ sitebuilder/ ai_chat/
```

Pre-existing lint issues exist in the codebase (82 findings, mostly unused imports); these are not regressions.

### Static files

Run `python3 manage.py collectstatic --noinput` before starting the dev server for the first time or after changing static assets. In `DEBUG=True` mode, WhiteNoise uses `CompressedStaticFilesStorage` which doesn't require a manifest.

### Key gotchas

- The system Python is `python3` (not `python`). Always use `python3` in commands.
- Pip installs to `~/.local/bin` which must be on `PATH`. The update script handles this.
- `python manage.py check --deploy` will show security warnings in dev (DEBUG=True, insecure SECRET_KEY, no SSL) — this is expected and not a problem for local development.
- Optional services (Redis, Celery, OpenAI, S3, OAuth providers) are all disabled by default and not needed for basic dev work.
- The `ai_chat` module requires `OPENAI_API_KEY` to function; without it, it falls back to rule-based responses.
