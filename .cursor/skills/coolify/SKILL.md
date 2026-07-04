---
name: coolify
description: >-
  Deploy Django apps with GitHub, Cloudflare (free plan), GCP, and Coolify.
  Covers GCP VM setup, Coolify services, Postgres, Docker/Gunicorn, DNS/SSL,
  OAuth redirects, and troubleshooting 502s. Use when the user mentions Coolify,
  deploy Django to GCP, Cloudflare DNS, GitHub deploy, or /coolify.
---

# Coolify — Django on GCP + GitHub + Cloudflare (free)

Deploy **Django + Gunicorn + PostgreSQL** using:

```
GitHub (source) → Coolify on GCP VM (build/run) → Cloudflare DNS + proxy (HTTPS)
```

**Default stack:** one **GCP Compute Engine** VM running **Coolify**, app as **Dockerfile** service, **Postgres** as Coolify database service, domain on **Cloudflare free** (proxied).

For fully managed GCP without Coolify, see [gcp-managed.md](gcp-managed.md) (Cloud Run + Cloud SQL).

---

## When to use this skill

- User says `/coolify`, Coolify deploy, or Django on GCP with Cloudflare
- Fixing **502 Bad Gateway** behind Cloudflare
- Wiring **GitHub → auto-deploy** on push
- Production env for Django (`DATABASE_URL`, OAuth, static/media)

---

## Architecture checklist

```
Task Progress:
- [ ] GCP: VM + static IP + firewall (22, 80, 443)
- [ ] Coolify installed on VM
- [ ] Postgres service in Coolify (v15+)
- [ ] Django app service (Dockerfile, port 8080 or 8000)
- [ ] GitHub repo connected + deploy webhook
- [ ] Cloudflare: A record → static IP (proxied)
- [ ] Env vars set in Coolify (see django-env.md)
- [ ] migrate + collectstatic on deploy
- [ ] /health/ returns ok
- [ ] OAuth redirect URIs updated for production domain
```

---

## 1. GCP — Compute Engine for Coolify

1. Create VM: **e2-standard-2** (or e2-medium for low traffic), **Ubuntu 22.04 LTS**, region near users.
2. Reserve **static external IP**; attach to VM.
3. Firewall / VPC: allow **22** (SSH, restrict to your IP), **80**, **443**.
4. SSH in and install Coolify (official one-liner from [coolify.io/docs](https://coolify.io/docs)):
   ```bash
   curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
   ```
5. Open Coolify UI: `http://STATIC_IP:8000` (first-run setup, admin account).
6. Optional: attach **GCP persistent disk** for backups/media if not using object storage.

**Do not** run production Postgres on the same disk without backups. Use Coolify’s Postgres service + scheduled backups.

---

## 2. GitHub — source and deploy

1. Push Django project (must include `Dockerfile`, `requirements.txt`, `manage.py`, WSGI path e.g. `drden.wsgi:application`).
2. In Coolify: **New Resource → Application → Public repo** (or GitHub App for private).
3. Select branch (e.g. `main` / `master`).
4. **Build pack:** Dockerfile (preferred for Django).
5. Enable **Auto Deploy** on push.
6. **Pre-deploy / post-deploy commands** (Coolify “Execute commands” or Dockerfile `RUN`):
   - Build time: `python manage.py collectstatic --noinput`
   - Deploy time (once per release): `python manage.py migrate --noinput`
7. **Health check path:** `/health/` (plain text `ok`).

**Dockerfile defaults for Django on Coolify:**

```dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD exec gunicorn --bind :8080 --workers 2 --threads 4 PROJECT.wsgi:application
```

Set Coolify **port** to match `EXPOSE`/CMD (8080 or 8000). Traefik terminates TLS at the edge.

---

## 3. Coolify — Postgres + Django app

### Postgres service

1. **New Resource → Database → PostgreSQL** (15+).
2. Note internal hostname (e.g. `postgres` or service UUID hostname) — **never `localhost`** from app container.
3. Link database to app or set env:
   - `DATABASE_URL=postgresql://USER:PASS@HOST:5432/DBNAME`
   - Or Coolify-injected `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (Django settings may read these).

### Django app service

1. Link Postgres resource.
2. Set env from [django-env.md](django-env.md).
3. **Persistent storage:** mount volume for `media/` **or** set `USE_S3_MEDIA=true` / GCS — container filesystem is ephemeral on redeploy.
4. Redeploy after env changes.

**Coolify-specific env (auto or manual):**

- `COOLIFY_FQDN` — public hostname (Coolify may inject)
- `COOLIFY_URL` — full URL with scheme
- `BASE_URL_SERVER=https://yourdomain.com`

Django apps with `SECURE_PROXY_SSL_HEADER` and `USE_X_FORWARDED_HOST` work behind Coolify Traefik + Cloudflare.

---

## 4. Cloudflare free plan — DNS and HTTPS

1. Add site to Cloudflare; update nameservers at registrar.
2. **DNS:** `A` record `@` → **GCP static IP**, **Proxied** (orange cloud).
3. `CNAME` `www` → `@` (proxied) if needed.
4. **SSL/TLS → Overview:** **Full (strict)** once origin has valid cert (Coolify/Let’s Encrypt).
5. **SSL/TLS → Edge Certificates:** Always Use HTTPS = On.
6. **Speed (optional):** Auto Minify off for admin if it breaks JS; Brotli on is fine.

**Free plan limits:** no WAF rules beyond basics; **100% uptime** proxy still applies. Rate limiting is limited — rely on Django middleware for scanner traffic if needed.

**OAuth / CSRF:** Production domain must appear in:

- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS` (https origins)
- Google/Facebook/etc. **Authorized redirect URIs**: `https://DOMAIN/auth/complete/google-oauth2/`

---

## 5. Django production env (minimum)

See [django-env.md](django-env.md) for full list. Required:

```env
DEBUG=False
SECRET_KEY=<random>
DATABASE_URL=postgresql://...
BASE_URL_SERVER=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SOCIAL_AUTH_REDIRECT_IS_HTTPS=True
```

Run **`migrate`** after each schema change. **`collectstatic`** before or during image build (WhiteNoise serves static files).

---

## 6. Verify deploy

```bash
curl -s https://yourdomain.com/health/
# expect: ok
```

Browser checks:

- Login / OAuth
- Admin `/admin/`
- File upload (confirm media storage not ephemeral)
- Stripe webhook URL if billing enabled

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|--------|----------------|-----|
| **502** from Cloudflare | App down, wrong port, crash on boot | Coolify logs; check `/health/` on origin IP:port; DB migrations |
| **502** intermittent | Container OOM or slow cold start | Increase VM RAM; reduce Gunicorn workers |
| **CSRF / OAuth redirect** | Wrong `CSRF_TRUSTED_ORIGINS` or redirect URI | Match exact https domain in env + Google Console |
| **Disappearing uploads** | Media on container disk | Volume mount or S3/GCS |
| **DB connection refused** | `localhost` in `DATABASE_URL` | Use Postgres **service hostname** from Coolify |
| **Static 404** | Missing collectstatic | Add to Dockerfile build step |
| **SSL loop** | Cloudflare Flexible + Django HTTPS redirect | Use **Full (strict)** |

---

## Agent workflow

When user asks to deploy or fix Coolify/GCP/Cloudflare Django hosting:

1. Confirm **Dockerfile**, **Postgres**, and **health** endpoint exist.
2. Read project `settings.py` for env var names (`DATABASE_URL`, `COOLIFY_*`, storage flags).
3. Draft Coolify env block from `django-env.md` + project `.env.example`.
4. List Cloudflare DNS + SSL steps and OAuth redirect URIs for their domain.
5. If 502: check health, logs, DB, port mapping before changing code.
6. Prefer **minimal diffs** — env and Dockerfile fixes over app refactors.

---

## Additional resources

- [django-env.md](django-env.md) — environment variable reference
- [gcp-managed.md](gcp-managed.md) — Cloud Run alternative (no Coolify)
