# GCP managed alternative (no Coolify)

Use when the user wants **fully managed** GCP instead of Coolify on a VM.

## Stack

| Component | Service |
|-----------|---------|
| App | **Cloud Run** (container from Dockerfile, port **8080**) |
| Database | **Cloud SQL PostgreSQL** |
| Media | **Cloud Storage** (+ django-storages GCS backend) |
| Secrets | **Secret Manager** |
| CI | **Cloud Build** triggered by **GitHub** push |
| DNS | **Cloudflare free** → Cloud Run URL or custom domain mapping |

## GitHub → Cloud Build → Cloud Run

1. Connect repo in Cloud Build triggers (GitHub App).
2. `cloudbuild.yaml` builds image → Artifact Registry.
3. Deploy to Cloud Run with Cloud SQL connector:

```bash
gcloud run deploy APP_NAME \
  --image REGION-docker.pkg.dev/PROJECT/REPO/app:latest \
  --region REGION \
  --port 8080 \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE \
  --set-env-vars "DEBUG=False,BASE_URL_SERVER=https://domain.com,..."
```

## Cloudflare + Cloud Run

- **Option A:** Cloud Run **domain mapping** for `yourdomain.com`; Cloudflare CNAME to `ghs.googlehosted.com` or A records per Google docs.
- **Option B:** Cloudflare proxied to Cloud Run URL (less common; verify SSL mode).

Same Django env as [django-env.md](django-env.md). **`DATABASE_URL`** uses Cloud SQL socket:

```
postgresql://USER:PASS@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE
```

## Migrations

Run via **Cloud Run Job** per release — not on every container instance startup.

## When to choose this over Coolify

- No VM patching; scale-to-zero possible
- Higher managed cost complexity but less SSH ops
- GDH `Dockerfile` already targets Cloud Run (`:8080`, Gunicorn)
