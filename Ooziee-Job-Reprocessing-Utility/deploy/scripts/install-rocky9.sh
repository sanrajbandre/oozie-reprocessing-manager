#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root (sudo)."
  exit 1
fi

APP_USER="${APP_USER:-ooziemgr}"
APP_GROUP="${APP_GROUP:-ooziemgr}"
APP_DIR="${APP_DIR:-/opt/oozie-reprocessing-manager}"
ENV_DIR="/etc/oozie-reprocessing"
ENV_FILE="${ENV_DIR}/oozie-reprocess.env"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "[1/8] Installing OS packages..."
dnf install -y \
  gcc gcc-c++ make \
  python3 python3-pip python3-devel \
  nodejs npm \
  git rsync \
  redis \
  mariadb-server mariadb \
  nginx

echo "[2/8] Enabling base services..."
systemctl enable --now redis
systemctl enable --now mariadb
systemctl enable --now nginx

echo "[3/8] Creating application service account..."
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /home/${APP_USER} --shell /sbin/nologin --user-group "${APP_USER}"
fi

mkdir -p "${APP_DIR}"
rsync -a --delete "${REPO_ROOT}/" "${APP_DIR}/"
chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"

echo "[4/8] Preparing Python virtual environments..."
runuser -u "${APP_USER}" -- python3 -m venv "${APP_DIR}/backend/.venv"
runuser -u "${APP_USER}" -- "${APP_DIR}/backend/.venv/bin/pip" install --upgrade pip wheel
runuser -u "${APP_USER}" -- "${APP_DIR}/backend/.venv/bin/pip" install -r "${APP_DIR}/backend/requirements.txt"

runuser -u "${APP_USER}" -- python3 -m venv "${APP_DIR}/worker/.venv"
runuser -u "${APP_USER}" -- "${APP_DIR}/worker/.venv/bin/pip" install --upgrade pip wheel
runuser -u "${APP_USER}" -- "${APP_DIR}/worker/.venv/bin/pip" install -r "${APP_DIR}/worker/requirements.txt"

echo "[5/8] Building frontend assets..."
runuser -u "${APP_USER}" -- bash -lc "cd '${APP_DIR}/frontend' && npm install --no-audit --no-fund && npm run build"

echo "[6/8] Installing environment + service files..."
mkdir -p "${ENV_DIR}"
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${APP_DIR}/deploy/env/oozie-reprocess.env.example" "${ENV_FILE}"
  chmod 640 "${ENV_FILE}"
  chown root:"${APP_GROUP}" "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Update secrets before starting app services."
fi

cp "${APP_DIR}/deploy/systemd/oozie-reprocess-api.service" /etc/systemd/system/oozie-reprocess-api.service
cp "${APP_DIR}/deploy/systemd/oozie-reprocess-worker.service" /etc/systemd/system/oozie-reprocess-worker.service
cp "${APP_DIR}/deploy/nginx/oozie-reprocess.conf" /etc/nginx/conf.d/oozie-reprocess.conf

echo "[7/8] Validating nginx and reloading systemd..."
nginx -t
systemctl daemon-reload
systemctl enable --now nginx

echo "[8/8] Deployment bootstrap complete."
echo "Next steps:"
echo "  1) Create DB and user, then load schema: ${APP_DIR}/scripts/mysql_schema.sql"
echo "  2) Edit ${ENV_FILE} with DB/JWT/Oozie values"
echo "  3) Start services: systemctl enable --now oozie-reprocess-api oozie-reprocess-worker"
echo "  4) Verify: systemctl status oozie-reprocess-api oozie-reprocess-worker && curl -sS http://127.0.0.1:8000/ready"
