#!/bin/bash
# =============================================================
# Koyal Portfolio - EC2 Server Setup Script
# Run this ONCE on a fresh Ubuntu 24.04 EC2 instance
# Usage: chmod +x setup-server.sh && sudo ./setup-server.sh
# =============================================================

set -e

APP_NAME="koyal"
APP_DIR="/var/www/koyal"
REPO_URL="$1"  # Pass your GitHub repo URL as argument
USER="ubuntu"

echo "🚀 Starting Koyal server setup..."

# --- 1. System updates ---
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# --- 2. Install dependencies ---
echo "📦 Installing Python, Nginx, PostgreSQL, Git..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    git \
    certbot \
    python3-certbot-nginx \
    curl \
    ufw \
    postgresql \
    postgresql-contrib

# --- 2b. Set up PostgreSQL database ---
echo "🗄️ Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE koyal_db;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "CREATE USER koyal_user WITH PASSWORD 'koyal_secure_pw_2024';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "ALTER ROLE koyal_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE koyal_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE koyal_user SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE koyal_db TO koyal_user;"
sudo -u postgres psql -c "ALTER DATABASE koyal_db OWNER TO koyal_user;"
echo "⚠️  IMPORTANT: Change the database password in /var/www/koyal/.env!"

# --- 3. Configure firewall ---
echo "🔒 Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# --- 4. Clone repository ---
echo "📥 Cloning repository..."
if [ -z "$REPO_URL" ]; then
    echo "⚠️  No repo URL provided. Usage: ./setup-server.sh https://github.com/user/koyal.git"
    echo "   Skipping clone — you can clone manually later."
else
    rm -rf $APP_DIR
    git clone $REPO_URL $APP_DIR
    chown -R $USER:$USER $APP_DIR
fi

# --- 5. Python virtual environment ---
echo "🐍 Setting up Python environment..."
cd $APP_DIR
sudo -u $USER python3 -m venv venv
sudo -u $USER bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# --- 6. Create .env from example ---
if [ ! -f "$APP_DIR/.env" ]; then
    echo "📝 Creating .env file from example..."
    sudo -u $USER cp .env.example .env
    echo "⚠️  IMPORTANT: Edit /var/www/koyal/.env with your production values!"
fi

# --- 7. Run Django setup ---
echo "🗄️ Running Django migrations..."
sudo -u $USER bash -c "cd $APP_DIR && source venv/bin/activate && python manage.py migrate --noinput"
sudo -u $USER bash -c "cd $APP_DIR && source venv/bin/activate && python manage.py collectstatic --noinput"

# --- 8. Create Gunicorn systemd service ---
echo "⚙️ Creating Gunicorn service..."
cat > /etc/systemd/system/koyal.service << 'EOF'
[Unit]
Description=Koyal Portfolio Gunicorn Daemon
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/koyal
EnvironmentFile=/var/www/koyal/.env
ExecStart=/var/www/koyal/venv/bin/gunicorn koyal.wsgi:application \
    --bind 127.0.0.1:8012 \
    --workers 2 \
    --timeout 120 \
    --access-logfile /var/log/koyal-access.log \
    --error-logfile /var/log/koyal-error.log
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable koyal
systemctl start koyal

# --- 9. Configure Nginx ---
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/koyal << 'EOF'
server {
    listen 80;
    server_name koyal.designrden.com www.koyal.designrden.com;

    client_max_body_size 20M;

    # Gzip compression
    gzip on;
    gzip_comp_level 5;
    gzip_min_length 256;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;

    # Static files (served by Nginx directly)
    location /static/ {
        alias /var/www/koyal/staticfiles/;
        expires 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
        access_log off;
    }

    # Media files
    location /media/ {
        alias /var/www/koyal/media/;
        expires 30d;
        access_log off;
    }

    # Django app
    location / {
        proxy_pass http://127.0.0.1:8012;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/koyal /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# --- 10. Allow ubuntu user to restart service without password ---
echo "🔑 Setting up sudoers for deploy..."
echo "ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart koyal, /bin/systemctl status koyal" > /etc/sudoers.d/koyal-deploy
chmod 440 /etc/sudoers.d/koyal-deploy

# --- Done ---
echo ""
echo "============================================="
echo "✅ Server setup complete!"
echo "============================================="
echo ""
echo "Next steps:"
echo "  1. Edit your .env:  nano /var/www/koyal/.env"
echo "  2. Create admin:    cd /var/www/koyal && source venv/bin/activate && python manage.py createsuperuser"
echo "  3. Get SSL cert:    sudo certbot --nginx -d koyal.designrden.com -d www.koyal.designrden.com"
echo "  4. Set up GitHub Secrets:"
echo "     - EC2_HOST = $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo '<your-ec2-ip>')"
echo "     - EC2_USER = ubuntu"
echo "     - EC2_SSH_KEY = <contents of your .pem file>"
echo ""
echo "Your site will be live at: http://koyal.designrden.com"
echo "============================================="
