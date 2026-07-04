# Django environment variables (Coolify / GCP / Cloudflare)

Copy into Coolify **Environment Variables** for the application service. Adjust domain and secrets.

## Core

| Variable | Example | Notes |
|----------|---------|--------|
| `DEBUG` | `False` | Never `True` in production |
| `SECRET_KEY` | long random string | Required |
| `BASE_URL_SERVER` | `https://designrden.com` | Canonical public URL |
| `ALLOWED_HOSTS` | `designrden.com,www.designrden.com` | Comma-separated |
| `CSRF_TRUSTED_ORIGINS` | `https://designrden.com,https://www.designrden.com` | Must include scheme |
| `CANONICAL_REDIRECT_SCHEME` | `https` | If canonical host redirects enabled |

## Database (PostgreSQL)

Use **one** of:

```env
DATABASE_URL=postgresql://USER:PASSWORD@postgres:5432/dbname
```

Or discrete (Coolify Postgres):

```env
POSTGRES_HOST=<internal-service-hostname>
POSTGRES_PORT=5432
POSTGRES_DB=drden
POSTGRES_USER=drden
POSTGRES_PASSWORD=<secret>
```

Never use `localhost` or `127.0.0.1` for DB host from inside the app container.

Optional: `DB_AUTO_CREATE=false` in production if DB is pre-created.

## Coolify (often auto-injected)

| Variable | Purpose |
|----------|---------|
| `COOLIFY_FQDN` | Public FQDN |
| `COOLIFY_URL` | Full deployment URL |

Ensure `BASE_URL_SERVER` matches the **Cloudflare** public domain if using custom domain (not only the Coolify default subdomain).

## HTTPS / proxy

```env
SOCIAL_AUTH_REDIRECT_IS_HTTPS=True
```

Django should have (typical production):

- `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`
- `USE_X_FORWARDED_HOST = True`

Cloudflare **Full (strict)** + Coolify TLS = correct `request.is_secure()` behavior.

## Static files

Static: **WhiteNoise** + `collectstatic` at **Docker build** time.

```dockerfile
RUN python manage.py collectstatic --noinput
```

No extra env required unless using custom `STATIC_ROOT`.

## Media (uploads)

**Option A — object storage (recommended):**

```env
USE_S3_MEDIA=true
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_REGION_NAME=us-east-1
```

**Option B — Coolify persistent volume:**

Mount host path to `/app/media` (or `MEDIA_ROOT` path). Set `SERVE_MEDIA=true` only if intentionally serving from Django.

## OAuth (Google example)

```env
GOOGLE_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...
```

Google Console redirect URI:

```
https://YOUR_DOMAIN/auth/complete/google-oauth2/
```

Also configure LinkedIn/Facebook/Instagram if enabled — path pattern:

```
https://YOUR_DOMAIN/auth/complete/<backend-name>/
```

## Email

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...   # or GMAIL_APP_PASSWORD
DEFAULT_FROM_EMAIL=designrden <noreply@yourdomain.com>
```

## Stripe (if used)

```env
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Webhook URL: `https://YOUR_DOMAIN/...` (match project URL config).

## Optional services

```env
OPENAI_API_KEY=...          # Designer AI
REDIS_URL=redis://...       # If Celery/cache enabled
USE_REDIS=True
```

## Deploy commands (Coolify)

**Post-deploy (once per release):**

```bash
python manage.py migrate --noinput
```

**Optional:**

```bash
python manage.py check --deploy
python manage.py createsuperuser  # interactive — run via Coolify terminal once
```

## Health check

Path: `/health/`  
Expected response: `ok` (200)
