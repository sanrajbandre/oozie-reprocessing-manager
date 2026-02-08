# Deployment Guide (CentOS 7 / Rocky 9)

## Components
- API (FastAPI): port 8000
- Worker: background task executor
- Redis: Pub/Sub for WebSocket events
- MySQL/MariaDB: persistent storage
- Frontend: Vite dev server (dev) or static build served by nginx (prod)

## Rocky 9 quickstart
```bash
sudo dnf install -y python3 python3-pip git redis mysql-server
sudo systemctl enable --now redis mysqld
mysql -u root -p < scripts/mysql_schema.sql
```

## CentOS 7 (Python 3.8+ via pyenv)
```bash
sudo yum groupinstall -y "Development Tools"
sudo yum install -y openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel wget curl git
curl https://pyenv.run | bash
# restart shell
pyenv install 3.8.18
pyenv global 3.8.18
```

## Backend
```bash
cd backend
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Worker
```bash
cd worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OOZIE_BIN=/usr/bin/oozie   # optional
export PRE_TASK_SHELL_CMD="kinit -kt /path/keytab principal"  # optional
python runner.py
```

## Frontend
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Default first-run admin:
- admin / admin123

## Systemd (production)
Copy repo to `/opt/oozie-reprocessing-manager`, then:
```bash
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oozie-reprocess-api oozie-reprocess-worker
```
