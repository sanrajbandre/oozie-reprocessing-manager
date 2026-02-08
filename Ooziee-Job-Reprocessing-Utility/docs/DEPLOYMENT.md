# Production Deployment Guide (Rocky Linux 9.x / CentOS Stream 9)

As of February 8, 2026, there is no "CentOS Linux 9" release. Use **CentOS Stream 9** or **Rocky Linux 9.x**.

This guide deploys:
- FastAPI API (`127.0.0.1:8000` via systemd + gunicorn)
- Worker service (systemd)
- Redis (events + websocket fanout)
- MariaDB/MySQL (persistent storage)
- Nginx (frontend static files + reverse proxy)

## 1) Server prerequisites

Run on a fresh Rocky 9.x / CentOS Stream 9 host as root/sudo.

```bash
sudo dnf update -y
sudo dnf install -y git
```

## 2) Copy source code to server

```bash
cd /opt
sudo git clone https://github.com/sanrajbandre/oozie-reprocessing-manager.git
cd /opt/oozie-reprocessing-manager/Ooziee-Job-Reprocessing-Utility
```

## 3) Automated install (recommended)

```bash
cd /opt/oozie-reprocessing-manager/Ooziee-Job-Reprocessing-Utility
sudo bash deploy/scripts/install-rocky9.sh
```

What the script does:
- Installs Python/Node/Nginx/Redis/MariaDB packages
- Creates system user `ooziemgr`
- Syncs app to `/opt/oozie-reprocessing-manager`
- Builds backend/worker virtualenvs
- Builds frontend assets (`frontend/dist`)
- Installs systemd + nginx config templates
- Creates `/etc/oozie-reprocessing/oozie-reprocess.env` if missing

## 4) Initialize database

Set root DB password (example shown):

```bash
export MYSQL_ROOT_PASSWORD='REPLACE_ROOT_PASSWORD'
export DB_NAME='oozie_reprocess'
export DB_USER='ooziemgr'
export DB_PASS='REPLACE_DB_PASSWORD'
export DB_HOST='127.0.0.1'

sudo -E bash /opt/oozie-reprocessing-manager/deploy/scripts/init-db.sh
```

## 5) Configure runtime environment

Edit:

```bash
sudo vi /etc/oozie-reprocessing/oozie-reprocess.env
```

Mandatory values to set:
- `DB_URL`
- `JWT_SECRET` (32+ chars)
- `CORS_ORIGINS`
- `OOZIE_DEFAULT_URL`

First-time bootstrap only:
- `BOOTSTRAP_ADMIN_ENABLED=true`
- `BOOTSTRAP_ADMIN_PASS=<strong temp password>`

## 6) Start API + worker + nginx

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now oozie-reprocess-api oozie-reprocess-worker nginx redis mariadb
```

## 7) Validate deployment

```bash
sudo systemctl status oozie-reprocess-api oozie-reprocess-worker --no-pager
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/ready
```

From a browser, open:

```text
http://<server-ip-or-fqdn>/
```

## 8) Disable bootstrap admin after first login

After creating permanent admin users from UI/API:

```bash
sudo sed -i 's/^BOOTSTRAP_ADMIN_ENABLED=.*/BOOTSTRAP_ADMIN_ENABLED=false/' /etc/oozie-reprocessing/oozie-reprocess.env
sudo systemctl restart oozie-reprocess-api
```

## 9) Firewall

Open only required ports:

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

Keep Redis/MySQL closed to public network.

If SELinux is enforcing (default), allow nginx reverse proxy connections:

```bash
sudo setsebool -P httpd_can_network_connect 1
```

## 10) Upgrade procedure

```bash
cd /opt/oozie-reprocessing-manager
sudo git pull
cd /opt/oozie-reprocessing-manager/backend
sudo -u ooziemgr .venv/bin/pip install -r requirements.txt
cd /opt/oozie-reprocessing-manager/worker
sudo -u ooziemgr .venv/bin/pip install -r requirements.txt
cd /opt/oozie-reprocessing-manager/frontend
sudo -u ooziemgr npm install --no-audit --no-fund
sudo -u ooziemgr npm run build
sudo systemctl restart oozie-reprocess-api oozie-reprocess-worker nginx
```

## Manual path (without install script)

If you prefer explicit manual commands, follow the same order above and use:
- `deploy/systemd/*.service` for systemd units
- `deploy/nginx/oozie-reprocess.conf` for nginx
- `deploy/env/oozie-reprocess.env.example` for environment file template
