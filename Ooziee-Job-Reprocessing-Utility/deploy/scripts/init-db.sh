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
DB_PORT="${DB_PORT:-3306}"
DB_AUTH_PLUGIN="${DB_AUTH_PLUGIN:-caching_sha2_password}" # mysql8 default
MYSQL_ROOT_USER="${MYSQL_ROOT_USER:-root}"
MYSQL_BIN="${MYSQL_BIN:-mysql}"
MYSQL_CONNECT_EXPIRED_PASSWORD="${MYSQL_CONNECT_EXPIRED_PASSWORD:-false}"

if [[ -z "${MYSQL_ROOT_PASSWORD:-}" && -z "${MYSQL_DEFAULTS_FILE:-}" ]]; then
  echo "Set MYSQL_ROOT_PASSWORD or MYSQL_DEFAULTS_FILE before running."
  exit 1
fi

if [[ -n "${DB_AUTH_PLUGIN}" ]]; then
  case "${DB_AUTH_PLUGIN}" in
    caching_sha2_password|mysql_native_password|sha256_password)
      ;;
    *)
      echo "Unsupported DB_AUTH_PLUGIN='${DB_AUTH_PLUGIN}'"
      exit 1
      ;;
  esac
fi

MYSQL_ARGS=()
if [[ -n "${MYSQL_DEFAULTS_FILE:-}" ]]; then
  MYSQL_ARGS+=(--defaults-extra-file="${MYSQL_DEFAULTS_FILE}")
fi
MYSQL_ARGS+=(-u"${MYSQL_ROOT_USER}")
if [[ -n "${MYSQL_ROOT_PASSWORD:-}" ]]; then
  MYSQL_ARGS+=(-p"${MYSQL_ROOT_PASSWORD}")
fi
if [[ "${MYSQL_CONNECT_EXPIRED_PASSWORD}" == "true" ]]; then
  MYSQL_ARGS+=(--connect-expired-password)
fi

if [[ -n "${DB_AUTH_PLUGIN}" ]]; then
  USER_IDENTIFIED_CLAUSE="IDENTIFIED WITH ${DB_AUTH_PLUGIN} BY '${DB_PASS}'"
else
  USER_IDENTIFIED_CLAUSE="IDENTIFIED BY '${DB_PASS}'"
fi

"${MYSQL_BIN}" "${MYSQL_ARGS[@]}" <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'${DB_HOST}' ${USER_IDENTIFIED_CLAUSE};
ALTER USER '${DB_USER}'@'${DB_HOST}' ${USER_IDENTIFIED_CLAUSE};
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'${DB_HOST}';
FLUSH PRIVILEGES;
SQL

"${MYSQL_BIN}" "${MYSQL_ARGS[@]}" "${DB_NAME}" < "${APP_DIR}/scripts/mysql_schema.sql"

echo "Database initialized."
echo "Set DB_URL in /etc/oozie-reprocessing/oozie-reprocess.env to:"
echo "  mysql+pymysql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}?charset=utf8mb4"
