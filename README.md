GlobalDesignerHub.com is a secure, tech-forward application designed for fashion designers to effortlessly upload and manage their design portfolios with detailed, clean, and organized tech pack information.
The platform offers a user-friendly interface and a robust authentication system, allowing users (including staff admins) to sign in securely via Google, LinkedIn, or Instagram OAuth flows or with traditional credentials. Built with both usability and security in mind, GlobalDesignerHub.com streamlines the process of presenting, storing, and sharing professional design documents in the fashion industry.

## Local development (runserver)

The Django dev server **only supports HTTP**, not HTTPS. To avoid `ERR_SSL_PROTOCOL_ERROR` or "Connection Failed":

1. Start the server: `python manage.py runserver` (default port 8000) or `python manage.py runserver 8006`.
2. **In your browser, open `http://127.0.0.1:8006`** (or `http://127.0.0.1:8000`) — use **`http://`**, not `https://`.

If the address bar shows `https://`, change it to `http://` or type the full URL with `http://` explicitly.

## Database + deployment notes (Docker/Coolify)

This app is intended to run on **PostgreSQL** in production.

### Coolify steps (Postgres service)

1. Create a Postgres service (v15+).
2. **Do not use `localhost` inside containers**: use the **service name / internal hostname** (commonly `postgres` or `db`).
3. Link the Postgres service to the app (Coolify injects `POSTGRES_*` env vars) or copy those values into the app env.
4. Set **either** `DATABASE_URL` **or** the discrete variables listed below, then redeploy.
   - If `DATABASE_URL` is left as the example `USER:PASSWORD@HOST`, the app ignores it and expects the `DB_*` vars.

### App configuration (repo)

- `gdh/settings.py` reads `DATABASE_URL` first; otherwise it uses `DB_*` or `POSTGRES_*/PG*` equivalents.
- `.env.example` lists the supported variables for local dev and hosting providers.
- There is **no SQLite fallback** in production; tests use in-memory SQLite.
- Discrete vars (if not using `DATABASE_URL`):
  - `DB_HOST`, `DB_PORT` (usually `5432`)
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`
  - Coolify equivalents: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`

### Restore + bootstrap (production)

- `python manage.py wait_for_db` now auto-creates the database if it is missing.
  - Disable with `DB_AUTO_CREATE=false` if you want to manage DB creation manually.
- To restore data on startup:
  - Set `AUTO_RESTORE_DB=1` to load the latest `backups/db-*.json.gz` from default storage.
  - Or set `RESTORE_DB_INPUT=backups/<file>.json.gz` to restore a specific backup.
- Backups are created with `python manage.py backup_db` and stored under `media/backups/`
  (or S3 when `USE_S3_MEDIA=true`).

### Other deployment notes

- **Migrations**: after deploying new code, run `python manage.py migrate` on the production database so new features (e.g. **Messenger** at `/messenger/`) work. If `/messenger/` returns 500, the chat tables may be missing — run `migrate` and retry.
- **Static files**: run `python manage.py collectstatic --noinput` as part of your build/release. Static assets are served via WhiteNoise.
- **Container cleanup logs**: during rolling updates some platforms auto-remove build containers. If you see `No such container` while cleaning up, it is usually safe. For custom automation, use `./docker_cleanup.sh <container>` to make cleanup idempotent.
- **Orphan container warnings**: after renaming/removing services, you may see "Found orphan containers". Run your deploy with `--remove-orphans` (or use your platform's cleanup action) to remove the old containers.
- **Email env warnings**: if you see `GMAIL_APP_PASSWORD` not set in Docker logs, it's an optional alias for `EMAIL_HOST_PASSWORD`. Set it to the same value (or remove it from your platform env list) to silence the warning.

## Authentication highlights

- OAuth providers: enable any mix of Google, LinkedIn, and Instagram by setting the corresponding `SOCIAL_AUTH_*_KEY` and `SOCIAL_AUTH_*_SECRET` env variables. The login view automatically surfaces only the providers that are configured, and staff can use the same flow (set `?next=/admin/` to jump back into Django admin after signing in).
- Email-first login: the custom `EmailOrUsernameModelBackend` allows either usernames or email addresses when using passwords.
- Passkey support: WebAuthn endpoints remain available for designers who prefer password-less sign-in.
- Automatic onboarding email: successful registrations—via forms, API, or OAuth—trigger a welcome email to the designer and a notification to the site owner.
- Password hygiene: forgot-password requests notify admins, and successful resets send a confirmation email to the account owner for additional visibility.

## Suspicious traffic filtering

The server now short-circuits obvious scanner traffic (e.g., `/wp-admin`, `*.php`, `/lander/...`) via `designer_portfolio.middleware.SuspiciousRequestThrottleMiddleware`.  
Configuration knobs (all optional) can be set via environment variables:

- `SUSPICIOUS_REQUEST_FILTER_ENABLED` (default: `True` when `DEBUG` is false) — disable entirely if you need to debug custom routes.
- `SUSPICIOUS_PATH_PATTERNS` — comma or newline separated regex patterns to match additional paths; if unset, sensible defaults are used.
- `SUSPICIOUS_REQUEST_RATE_LIMIT` — maximum number of suspicious hits per IP within the window (default: `120`).
- `SUSPICIOUS_REQUEST_RATE_WINDOW` — window length in seconds for the above rate limit (default: `60`).

Filtered responses include the `X-Request-Filtered: suspicious` header and will return either `404` or `429` when the rate limit triggers.

## Automated repository housekeeping

A scheduled GitHub Action (`.github/workflows/cleanup-unused-branches.yml`) keeps the hosted repository tidy by pruning feature branches that have been inactive for 45 days. The job runs every Monday at 06:00 UTC (and can also be triggered manually with `workflow_dispatch`) and executes `.github/scripts/cleanup_branches.py`, which calls the GitHub API to:

- Skip protected/default branches, well-known prefixes (`release/*`, `dependabot/*`, etc.), and branches linked to open PRs.
- Respect configurable limits via environment variables such as `BRANCH_STALE_DAYS`, `BRANCH_DELETE_LIMIT`, and `PROTECTED_BRANCHES`.
- Support a dry-run mode on manual invocations so the proposed deletions can be reviewed safely before applying.

Update the workflow inputs or the script’s environment variables if you need different retention windows or protected branch rules.
