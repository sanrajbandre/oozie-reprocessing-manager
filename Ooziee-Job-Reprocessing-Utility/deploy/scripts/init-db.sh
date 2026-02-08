#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root (sudo)."
  exit 1
fi

APP_DIR="${APP_DIR:-/opt/oozie-reprocessing-manager}"
DB_NAME="${DB_NAME:-oozie_reprocess}"
DB_USER="${DB_USER:-ooziemgr}"
DB_PASS="${DB_PASS:-change_me}"
DB_HOST="${DB_HOST:-127.0.0.1}"

if [[ -z "${MYSQL_ROOT_PASSWORD:-}" ]]; then
  echo "Set MYSQL_ROOT_PASSWORD in environment before running."
  exit 1
fi

mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'${DB_HOST}' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'${DB_HOST}';
FLUSH PRIVILEGES;
SQL

mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" "${DB_NAME}" < "${APP_DIR}/scripts/mysql_schema.sql"

echo "Database initialized."
echo "Set DB_URL in /etc/oozie-reprocessing/oozie-reprocess.env to:"
echo "  mysql+pymysql://${DB_USER}:${DB_PASS}@${DB_HOST}:3306/${DB_NAME}?charset=utf8mb4"
