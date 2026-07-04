# designrden (drden)

A global platform for Fashion, Graphic, UX/UI, Interior, Product, Animation, and Digital Designers to build professional portfolios, connect with recruiters, explore career opportunities, and leverage AI-powered creative tools.

**Live:** https://designrden.com

---

## Tech Stack

- Django 5.2+
- Django REST Framework (DRF)
- PostgreSQL (Production)
- SQLite (Development)
- Cloudflare R2 (S3-compatible) for static/media storage
- Gunicorn
- Nginx
- WhiteNoise
- Redis (optional)
- Celery (optional)
- Docker & Docker Compose
- GitHub Actions (CI/CD)
- Bootstrap 5 / Tailwind CSS
- JavaScript

---

## Features

- Designer Portfolio Builder
- Personalized Portfolio Websites
- Free Portfolio Subdomains
- AI Portfolio Assistant
- Portfolio Templates
- Designer Profiles
- Design Communities
- Job & Internship Portal
- Courses & Certifications
- AI Chatbot
- Portfolio Analytics
- Resume Builder
- Employer Dashboard
- Student Dashboard
- Admin Dashboard

---

## Local Development

```bash
# Clone repository
git clone https://github.com/aiOakuser/git
cd drden

# Create virtual environment
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Update environment variables

python manage.py migrate

python manage.py collectstatic --noinput

python manage.py runserver
```

---

## Environment Variables

Copy `.env.example` to `.env`.

| Variable | Description |
|-----------|-------------|
| ENV | production / development |
| DEBUG | True / False |
| SECRET_KEY | Django secret key |
| ALLOWED_HOSTS | Allowed domains |
| CSRF_TRUSTED_ORIGINS | Trusted origins |
| DB_ENGINE | django.db.backends.postgresql |
| DB_NAME | PostgreSQL database |
| DB_USER | Database user |
| DB_PASSWORD | Database password |
| DB_HOST | Database host |
| DB_PORT | PostgreSQL port |
| USE_R2 | Enable Cloudflare R2 |
| R2_ACCESS_KEY_ID | Cloudflare Access Key |
| R2_SECRET_ACCESS_KEY | Cloudflare Secret |
| R2_BUCKET_NAME | Storage bucket |
| R2_ACCOUNT_ID | Cloudflare Account ID |
| R2_PUBLIC_DOMAIN | Public R2 Domain |
| EMAIL_HOST | SMTP host |
| EMAIL_HOST_USER | SMTP email |
| EMAIL_HOST_PASSWORD | SMTP password |
| DEFAULT_FROM_EMAIL | Sender email |

---

# Deployment (AWS EC2)

## Quick Start

Launch Ubuntu EC2.

```bash
sudo apt update

cd /var/www

git clone https://github.com/aiOakuser/git

cd drden

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate

python manage.py collectstatic --noinput
```

Configure Gunicorn

```bash
gunicorn wsgi:application
```

Configure Nginx

```bash
sudo nginx -t

sudo systemctl restart nginx
```

---

## SSL

Install Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx

sudo certbot --nginx -d designrden.com -d www.designrden.com
```

---

## GitHub Actions

Every push to `main` automatically deploys the application.

Required GitHub Secrets

- EC2_HOST
- EC2_USER
- EC2_SSH_KEY
- DJANGO_SECRET_KEY
- DATABASE_URL

---

## Cloudflare R2

Static files, media, portfolios, resumes, and project images are stored in Cloudflare R2.

Required Variables

- R2_ACCESS_KEY_ID
- R2_SECRET_ACCESS_KEY
- R2_BUCKET_NAME
- R2_ACCOUNT_ID
- R2_PUBLIC_DOMAIN

---

# Project Structure

```text
drden/
│
├── .github/
│   └── workflows/
│
├── ai_chat/
├── deploy/
├── designer_portfolio/
│
├── ai/
├── data/
├── forms/
├── management/
│   ├── __pycache__/
│   ├── commands/
│   ├── __init__.py
│   └── migrations/
│
├── services/
├── static/
│   ├── css/
│   ├── images/
│   ├── js/
│   ├── swatches/
│   └── videos/
│
├── templates/
│
├── admin.py
├── apps.py
├── auth_backends.py
├── auth_utils.py
├── constants.py
├── context_processors.py
├── core_designers.py
├── emails.py
├── forms.py
├── membership_plans.py
├── messenger_utils.py
├── middleware.py
├── mobile_api.py
├── models.py
├── project_templates.py
├── recaptcha_utils.py
├── serializers.py
├── signals.py
├── social_pipeline.py
├── social_providers.py
├── stripe_billing.py
├── student_portfolio_templates.py
├── student_portfolio_views.py
├── tasks.py
├── tests.py
├── urls.py
├── utils.py
├── views.py
│
├── docs/
├── env/
├── drden/
├── marketing/
├── media/
├── mobile/
├── sitebuilder/
├── staticfiles/
│
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── README.md
├── requirements.txt
├── LICENSE
└── DESIGNSYSTEM.md
---


# REST API
```
GET /api/designers/
GET /api/portfolios/
GET /api/jobs/
GET /api/courses/
GET /api/certifications/
GET /api/chatbot/
GET /api/profile/
GET /health/
```

---

# Useful EC2 Commands

## Activate virtual environment

```bash
cd /var/www/drden

source venv/bin/activate
```

---

## Run migrations

```bash
python manage.py migrate
```

---

## Collect static files

```bash
python manage.py collectstatic --noinput
```

---

## Restart Gunicorn

```bash
sudo systemctl restart gunicorn
```

or

```bash
sudo systemctl restart drden
```

(if your service is named `service`)

---

## Restart Nginx

```bash
sudo systemctl restart nginx
```

---

## View Gunicorn logs

```bash
sudo journalctl -u gunicorn -f
```

---

## View Nginx logs

```bash
sudo tail -f /var/log/nginx/error.log
```

---

## Check running services

```bash
sudo systemctl status gunicorn

sudo systemctl status nginx
```

---

## Backup PostgreSQL

```bash
/var/www/drden/deploy/backup-db.sh
```

---

## Django shell

```bash
cd /var/www/drden

source venv/bin/activate

python manage.py shell
```

---

## Update application

```bash
git pull origin main

source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate

python manage.py collectstatic --noinput

sudo systemctl restart gunicorn

sudo systemctl restart nginx
```

---

## License

Copyright © AIOAK Inc.

designrden is a platform developed and maintained by **AIOAK Inc.**





# drden Portfolio — Deployment Guide (AWS EC2 Free Tier + GitHub Actions)

## Prerequisites

- AWS account (https://aws.amazon.com — free tier eligible)
- GitHub account with drden repo pushed
- Cloudflare account with R2 bucket (`designrden-storage`)
- Domain DNS managed by Cloudflare

---

## STEP 1: Push Code to GitHub

```bash
cd C:\Users\Yaswanth Reddy\OneDrive - vitap.ac.in\Desktop\drden

git add .
git commit -m "Add deployment configuration"
git push origin main
```

---

## STEP 2: Launch EC2 Instance

1. Go to https://console.aws.amazon.com/ec2
2. Click **"Launch Instance"**
3. Configure:

| Setting | Value |
|---------|-------|
| Name | `drden-portfolio` |
| AMI | Ubuntu Server 24.04 LTS (Free tier eligible) |
| Instance type | `t2.micro` (Free tier eligible) |
| Key pair | Create new → `uddap-rsa` → RSA → .pem → Download |
| Security Group | Allow SSH (22), HTTP (80), HTTPS (443) from Anywhere |
| Storage | 30 GB gp3 (Free tier eligible) |

4. Click **Launch Instance**

---

## STEP 3: Get Elastic IP (Static IP)

1. EC2 Console → **Elastic IPs** → **Allocate**
2. Select the new IP → **Actions** → **Associate** → Choose your instance

**Your Elastic IP: `3.132.60.87`**
3.132.60.87
---

## STEP 4: Connect to Server

```powershell
# Windows PowerShell
cd C:\Users\Yaswanth Reddy\Downloads
ssh -i uddap-rsa.pem ubuntu@3.132.60.87
```

If permissions error:
```powershell
icacls uddap-rsa.pem /inheritance:r /grant:r "%USERNAME%:R"
```

---

## STEP 5: Clone Repo & Setup

```bash
# As root
sudo -i

# Clone to /var/www/drden
git clone https://github.com/aiOakuser/git /var/www/drden
chown -R ubuntu:ubuntu /var/www/drden

# Run setup script
cd /var/www/drden/deploy
chmod +x setup-server.sh
./setup-server.sh
```

The setup script installs: Python, Nginx, PostgreSQL, creates database, venv, and runs migrations.

---

## STEP 6: Fix Storage Backend (if collectstatic fails)

If you see `MissingFileError` during collectstatic, fix the storage backend:

```bash
cd /var/www/drden
source venv/bin/activate
sed -i 's/CompressedManifestStaticFilesStorage/CompressedStaticFilesStorage/' drden/settings.py
python manage.py collectstatic --noinput --clear
```

---

## STEP 7: Configure .env

```bash
nano /var/www/drden/.env
```

Contents:
```
# --- Core ---
ENV=production
DEBUG=False
SECRET_KEY=<your-django-secret-key>

# --- Cloudflare R2 ---
USE_R2=True
R2_IMAGES_ENABLED=True
R2_ACCESS_KEY_ID=<your-key>
R2_SECRET_ACCESS_KEY=<your-secret>
R2_BUCKET_NAME=designrden-storage
R2_ACCOUNT_ID=<your-account-id>
R2_PUBLIC_DOMAIN=<your-public-domain>
R2_STATIC_LOCATION=drden_portfolio
R2_MEDIA_LOCATION=media
R2_MEDIA_LIST_CACHE_TIMEOUT=300

# --- Database ---
DB_ENGINE=django.db.backends.postgresql
DB_NAME=designer_db
DB_USER=designer_user
DB_PASSWORD=oakoak@123
DB_HOST=localhost
DB_PORT=5432

# --- Email ---
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<your-email-user>
EMAIL_HOST_PASSWORD=<your-email-password>
DEFAULT_FROM_EMAIL=no-reply@designrden.com
```

Save: `Ctrl+O` → Enter → `Ctrl+X`

```bash
sudo systemctl restart drden
```

### Get R2 Credentials from Cloudflare:

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Click **R2 Object Storage** → **Manage R2 API Tokens**
3. Click **Create API Token** → Permissions: Object Read & Write → Bucket: designrden-storage
4. Copy **Access Key ID** and **Secret Access Key**
5. **Account ID**: In your dashboard URL → `https://dash.cloudflare.com/<ACCOUNT_ID>/r2`
6. **Public Domain**: R2 → bucket → Settings → Public Access (e.g., `pub-xxxxx.r2.dev`)

---

## STEP 8: Create Gunicorn Service

```bash
sudo cat > /etc/systemd/system/service << 'EOF'
[Unit]
Description=drden Portfolio Gunicorn Daemon
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/drden
ExecStart=/var/www/drden/venv/bin/gunicorn wsgi:application --bind 127.0.0.1:8012 --workers 2 --timeout 120
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable drden
sudo systemctl start drden
sudo systemctl status drden
```

Should show **"active (running)"** in green.

---

## STEP 9: Configure Nginx

```bash
sudo cat > /etc/nginx/sites-available/drden << 'EOF'
server {
    listen 80;
    server_name designrden.com www.designrden.com _;

    client_max_body_size 20M;

    location /static/ {
        alias /var/www/drden/staticfiles/;
        expires 365d;
        access_log off;
    }

    location /media/ {
        alias /var/www/drden/media/;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8012;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/drden /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## STEP 10: Fix ALLOWED_HOSTS

If you see "DisallowedHost" error, fix it:

```bash
cd /var/www/drden
source venv/bin/activate

python -c "
path = '/var/www/drden/drden/settings.py'
with open(path) as f:
    content = f.read()
old = '\"127.0.0.1\", \"localhost\",\n    \"https://designrden.com\",\n    \"https://www.designrden.com\",'
new = '\"127.0.0.1\", \"localhost\",\n    \"3.132.60.87\",\n    \"designrden.com\",\n    \"www.designrden.com\",'
content = content.replace(old, new)
with open(path, 'w') as f:
    f.write(content)
print('Done')
"

sudo systemctl restart drden
```

---

## STEP 11: Test

```bash
curl http://localhost/health/
# Should return: {"status": "ok"}
```

Visit in browser: `https://designrden.com`

---

## DNS Setup ✅ COMPLETED

`designrden.com` → A record → `3.132.60.87` ✅

A CNAME for `www.designrden.com` is **optional**. If you want `www` to also work, in Cloudflare click **+ Add record**:

| Type | Name | Content |
|------|------|---------|
| CNAME | `www` | `designrden.com` |

But most portfolio sites just use the main domain without `www`. Your site is already accessible at:

**https://designrden.com** ✅

---

## STEP 12: Create Admin User ✅ COMPLETED

```bash
cd /var/www/drden && source venv/bin/activate
python manage.py createsuperuser
```

Admin credentials:
- **Username:** famtoodoos@gmail.com
- **Email:** famtoodoos@gmail.com
- **Password:** qwertyuiop

Admin panel: https://designrden.com/admin/

> ⚠️ Change this password to something stronger later via admin panel!

---

## STEP 13: SSL Certificate (HTTPS) ✅ COMPLETED

### Pre-requisite: Set DNS to "DNS only" (gray cloud) in Cloudflare

1. Go to Cloudflare DNS dashboard
2. Click **Edit** on `designrden.com` record
3. Click the orange cloud → turns gray (DNS only)
4. Save

### Run Certbot:

```bash
sudo certbot --nginx -d designrden.com
```

Prompts:
- Enter email: `yaswanth.arumulla@gmail.com`
- Agree to terms: `Y`
- Share email with EFF: `N`

Output on success:
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/designrden.com/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/designrden.com/privkey.pem
This certificate expires on 2026-09-27.
Certbot has set up a scheduled task to automatically renew this certificate.
Successfully deployed certificate for designrden.com to /etc/nginx/sites-enabled/drden
Congratulations! You have successfully enabled HTTPS on https://designrden.com
```

### After SSL is set up:

- Go back to Cloudflare and turn proxy back to **orange** (Proxied) if you want CDN
- Auto-renewal check: `sudo certbot renew --dry-run`
- Certificate expires 2026-09-27 (auto-renews)

---

## STEP 14: GitHub Actions Auto-Deploy

Go to GitHub → repo → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret | Value |
|--------|-------|
| `EC2_HOST` | `3.132.60.87` |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Full contents of `uddap-rsa.pem` (including BEGIN/END lines) |

Also grant ubuntu permission to restart without password:
```bash
echo "ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart drden, /bin/systemctl status drden" | sudo tee /etc/sudoers.d/drden-deploy
sudo chmod 440 /etc/sudoers.d/drden-deploy
```

Fix file ownership (important — prevents permission errors during deploy):
```bash
sudo chown -R ubuntu:ubuntu /var/www/drden
```

Now every `git push origin main` auto-deploys!

---

## DONE! ✅

- **Website:** https://designrden.com
- **Admin:** https://designrden.com/admin/
- **Health:** https://designrden.com/health/
- **API:** https://designrden.com/api/

### Deployment Progress:

- ✅ App running on EC2
- ✅ Domain connected (designrden.com)
- ✅ SSL (HTTPS) working (Certbot auto-renews)
- ⬜ Fix images (need R2 credentials from Cloudflare)
- ⬜ GitHub Actions auto-deploy (add secrets to GitHub)
- ⬜ Create admin user

---

## Daily Operations

```bash
# SSH into server
ssh -i uddap-rsa.pem ubuntu@3.132.60.87

# View logs
sudo journalctl -u drden -f

# Restart app
sudo systemctl restart drden

# Backup database
/var/www/drden/deploy/backup-db.sh

# Manual deploy (if GitHub Actions not set up)
cd /var/www/drden
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart drden
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 502 Bad Gateway | `sudo systemctl restart drden` then `sudo systemctl status drden` |
| DisallowedHost | Add IP/domain to ALLOWED_HOSTS in settings.py, restart |
| Images not loading | Check `USE_R2=True` and R2 credentials in .env |
| Static files missing | `python manage.py collectstatic --noinput` |
| collectstatic MissingFileError | Change to `CompressedStaticFilesStorage` in settings.py |
| Database connection refused | `sudo systemctl start postgresql` |
| SSL cert expired | `sudo certbot renew` |
| GitHub Actions fails | Check EC2_SSH_KEY secret has full .pem contents |
| Permission denied on restart | Set up sudoers (Step 14) |

---

## Cost Summary

| Resource | Cost |
|----------|------|
| EC2 t2.micro | FREE (12 months) |
| 30 GB storage | FREE (12 months) |
| Elastic IP | FREE (while instance runs) |
| SSL (Certbot) | FREE forever |
| Cloudflare DNS | FREE forever |
| Cloudflare R2 (10GB) | FREE forever |
| PostgreSQL (on EC2) | FREE (same instance) |
| **Total** | **$0/month** |

After 12 months: ~$8.50/month for EC2.

---

## How Future Updates Work (CI/CD)

**GitHub Actions handles everything automatically.** Once you set up the GitHub Secrets (Step 14), here's how it works:

### Normal workflow (no SSH needed):

```
1. Edit code locally (on your Windows machine)
2. git add . && git commit -m "your changes" && git push origin main
3. GitHub Actions automatically:
   - SSHs into your EC2
   - Pulls the latest code
   - Installs dependencies
   - Runs migrations
   - Collects static files
   - Restarts the app
4. Done — site is updated in ~30 seconds
```

**You never need to log into EC2 again for code changes.**

---

### When you DO need to SSH into EC2:

| Situation | Why |
|-----------|-----|
| Changing `.env` values (passwords, R2 keys) | `.env` is not in git — only exists on server |
| Server crashed / need to debug | Check logs with `journalctl` |
| SSL certificate issues | Run `certbot` commands |
| Database operations (backup, restore) | Direct DB access |
| First-time setup | One-time only |

---

### Summary:

- **Code changes** → just `git push` → GitHub Actions does everything
- **Environment/secrets changes** → SSH into EC2 and edit `.env`
- **Server issues** → SSH to debug

That's the beauty of CI/CD — push code, it deploys itself.

---

### About .env vs .env.example:

- **`.env`** → NOT in GitHub (blocked by `.gitignore`) — lives only on the EC2 server with real secrets
- **`.env.example`** → IS in GitHub — just a template with placeholder values (safe to share)

The `.env` on your server was created once during setup. GitHub Actions never overwrites it. Your secrets stay private.
