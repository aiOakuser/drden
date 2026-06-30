# GlobalDesignerHub (GDH)

A global platform for Fashion, Graphic, UX/UI, Interior, Product, Animation, and Digital Designers to build professional portfolios, connect with recruiters, explore career opportunities, and leverage AI-powered creative tools.

**Live:** https://globaldesignerhub.com

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
git clone https://github.com/aiOakuser/gdh.git
cd gdh

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

git clone https://github.com/aiOakuser/gdh.git

cd gdh

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate

python manage.py collectstatic --noinput
```

Configure Gunicorn

```bash
gunicorn gdh.wsgi:application
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

sudo certbot --nginx -d globaldesignerhub.com -d www.globaldesignerhub.com
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

```
gdh/
│
├── gdh/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── storages.py
│
├── designer/
├── portfolio/
├── jobs/
├── courses/
├── accounts/
├── ai_tools/
├── chatbot/
├── certifications/
├── dashboards/
├── api/
│
├── templates/
├── static/
├── media/
│
├── deploy/
│   ├── nginx/
│   ├── gunicorn.service
│   ├── deploy.sh
│   └── backup-db.sh
│
├── .github/
│   └── workflows/
│       └── deploy.yml
│
├── requirements.txt
├── manage.py
└── README.md
```

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
cd /var/www/gdh

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
sudo systemctl restart gdh
```

(if your service is named `gdh.service`)

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
/var/www/gdh/deploy/backup-db.sh
```

---

## Django shell

```bash
cd /var/www/gdh

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

GlobalDesignerHub is a platform developed and maintained by **AIOAK Inc.**

                        Internet
                            │
                     Cloudflare DNS
                            │
                    AWS EC2 (Ubuntu)
                            │
                         Nginx
          ┌─────────────────┴─────────────────┐
          │                                   │
globaldesignerhub.com                  designrden.com
          │                                   │
     Gunicorn #1                        Gunicorn #2
          │                                   │
   GDH Django App                    Designrden Django App



  sudo certbot --nginx \
  -d globaldesignerhub.com \
  -d www.globaldesignerhub.com \
  -d seri.globaldesignerhub.com \
  -d volumeone.globaldesignerhub.com