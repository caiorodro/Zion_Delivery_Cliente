#!/usr/bin/env bash
set -Eeuo pipefail

# Zion Delivery full installer for Ubuntu 24.04 LTS
# - MySQL 8 with concurrency tuning
# - Python 3.10.11 via pyenv
# - Backend (FastAPI) + Frontend (Flet) services
# - Nginx reverse proxy + HTTPS via certbot
# - Runtime logs in /tmp/zion_logs
# - Optional DB restore from baseZD2703.sql

############################
# Defaults (can be overridden via env)
############################
DOMAIN_API="${DOMAIN_API:-ziondelivery.app.br}"
DOMAIN_APP="${DOMAIN_APP:-loja.ziondelivery.app.br}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
ENABLE_HTTPS="${ENABLE_HTTPS:-1}"

SERVER_USER="${SERVER_USER:-zion}"
SERVER_GROUP="${SERVER_GROUP:-zion}"
BASE_DIR="${BASE_DIR:-/opt/zion}"
PROJECT_DIR="${PROJECT_DIR:-/opt/zion/Zion_Delivery_Cliente}"
GIT_REPO_URL="${GIT_REPO_URL:-}"
GIT_BRANCH="${GIT_BRANCH:-}"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-zion}"
DB_USERNAME="${DB_USERNAME:-root}"
DB_PASSWORD="${DB_PASSWORD:-56Runna01}"

# Backup SQL expected after project checkout
DB_RESTORE_FILE="${DB_RESTORE_FILE:-${PROJECT_DIR}/backend/migrations/baseZD2703.sql}"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
FLET_PORT="${FLET_PORT:-8080}"

LOG_DIR="${LOG_DIR:-/tmp/zion_logs}"
BACKEND_LOG_FILE="${BACKEND_LOG_FILE:-${LOG_DIR}/backend.log}"
FRONTEND_LOG_FILE="${FRONTEND_LOG_FILE:-${LOG_DIR}/frontend.log}"

# MySQL tuning defaults for moderate concurrency (8 GB RAM baseline)
MYSQL_MAX_CONNECTIONS="${MYSQL_MAX_CONNECTIONS:-300}"
MYSQL_INNODB_BUFFER_POOL_SIZE="${MYSQL_INNODB_BUFFER_POOL_SIZE:-4G}"
MYSQL_INNODB_BUFFER_POOL_INSTANCES="${MYSQL_INNODB_BUFFER_POOL_INSTANCES:-4}"
MYSQL_INNODB_LOG_FILE_SIZE="${MYSQL_INNODB_LOG_FILE_SIZE:-512M}"
MYSQL_THREAD_CACHE_SIZE="${MYSQL_THREAD_CACHE_SIZE:-100}"
MYSQL_TABLE_OPEN_CACHE="${MYSQL_TABLE_OPEN_CACHE:-4000}"
MYSQL_TABLE_DEFINITION_CACHE="${MYSQL_TABLE_DEFINITION_CACHE:-2000}"

log() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*" >&2
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "Run as root: sudo bash deploy/install_zion_ubuntu24_root.sh"
  fi
}

require_vars() {
  [[ -n "${GIT_REPO_URL}" ]] || die "GIT_REPO_URL is required."
  if [[ "${ENABLE_HTTPS}" == "1" ]]; then
    [[ -n "${CERTBOT_EMAIL}" ]] || die "CERTBOT_EMAIL is required when ENABLE_HTTPS=1."
  fi
}

apt_install_base() {
  log "Installing base packages"
  apt update
  DEBIAN_FRONTEND=noninteractive apt -y upgrade
  DEBIAN_FRONTEND=noninteractive apt -y install \
    git curl wget build-essential pkg-config software-properties-common \
    ca-certificates gnupg lsb-release ufw nginx
}

configure_firewall() {
  log "Configuring firewall"
  ufw allow OpenSSH || true
  ufw allow "Nginx Full" || true
  ufw --force enable || true
}

install_mysql() {
  log "Installing MySQL"
  DEBIAN_FRONTEND=noninteractive apt -y install mysql-server
  systemctl enable mysql
  systemctl start mysql
}

configure_mysql_root_and_schema() {
  log "Configuring root credentials and database"

  # Ensure root works both for localhost and 127.0.0.1 using password auth.
  mysql <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
FLUSH PRIVILEGES;
SQL
}

configure_mysql_concurrency() {
  log "Applying MySQL tuning"
  local conf_file="/etc/mysql/mysql.conf.d/mysqld.cnf"
  cp "${conf_file}" "${conf_file}.bak.$(date +%Y%m%d%H%M%S)"

  cat > /etc/mysql/mysql.conf.d/zzz-zion-tuning.cnf <<EOF
[mysqld]
max_connections = ${MYSQL_MAX_CONNECTIONS}
thread_cache_size = ${MYSQL_THREAD_CACHE_SIZE}
table_open_cache = ${MYSQL_TABLE_OPEN_CACHE}
table_definition_cache = ${MYSQL_TABLE_DEFINITION_CACHE}
skip_name_resolve = ON
performance_schema = ON

innodb_buffer_pool_size = ${MYSQL_INNODB_BUFFER_POOL_SIZE}
innodb_buffer_pool_instances = ${MYSQL_INNODB_BUFFER_POOL_INSTANCES}
innodb_log_file_size = ${MYSQL_INNODB_LOG_FILE_SIZE}
innodb_flush_log_at_trx_commit = 1
innodb_flush_method = O_DIRECT

tmp_table_size = 64M
max_heap_table_size = 64M
EOF

  systemctl restart mysql
}

install_python_build_deps() {
  log "Installing Python build dependencies"
  DEBIAN_FRONTEND=noninteractive apt -y install \
    make zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev libssl-dev
}

create_service_user() {
  if id -u "${SERVER_USER}" >/dev/null 2>&1; then
    log "User ${SERVER_USER} already exists"
  else
    log "Creating user ${SERVER_USER}"
    useradd -m -s /bin/bash "${SERVER_USER}"
  fi
}

install_pyenv_python() {
  log "Installing pyenv"
  su - "${SERVER_USER}" -c 'if [[ ! -d "$HOME/.pyenv" ]]; then curl https://pyenv.run | bash; fi'

  log "Installing Python 3.10.11"
  su - "${SERVER_USER}" -c 'export PATH="$HOME/.pyenv/bin:$PATH"; eval "$(pyenv init -)"; pyenv install -s 3.10.11; pyenv global 3.10.11'
}

checkout_project() {
  log "Cloning or updating project"
  mkdir -p "${BASE_DIR}"
  chown -R "${SERVER_USER}:${SERVER_GROUP}" "${BASE_DIR}"

  if [[ -d "${PROJECT_DIR}/.git" ]]; then
    if [[ -n "${GIT_BRANCH}" ]]; then
      su - "${SERVER_USER}" -c "cd '${PROJECT_DIR}' && git fetch --all && git checkout '${GIT_BRANCH}' && git pull --ff-only origin '${GIT_BRANCH}'"
    else
      su - "${SERVER_USER}" -c 'cd "'"${PROJECT_DIR}"'" && git fetch --all && DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD --short | sed "s@^origin/@@") && git checkout "$DEFAULT_BRANCH" && git pull --ff-only origin "$DEFAULT_BRANCH"'
    fi
  else
    if [[ -n "${GIT_BRANCH}" ]]; then
      su - "${SERVER_USER}" -c "cd '${BASE_DIR}' && git clone --branch '${GIT_BRANCH}' '${GIT_REPO_URL}' 'Zion_Delivery_Cliente'"
    else
      su - "${SERVER_USER}" -c "cd '${BASE_DIR}' && git clone '${GIT_REPO_URL}' 'Zion_Delivery_Cliente'"
    fi
  fi
}

setup_virtualenvs_and_dependencies() {
  log "Creating virtualenvs and installing dependencies"
  su - "${SERVER_USER}" -c '
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    cd "'"${PROJECT_DIR}"'"

    python -m venv .venv_backend
    source .venv_backend/bin/activate
    pip install --upgrade pip wheel setuptools
    pip install -r requirements_backend.txt
    deactivate

    python -m venv .venv_frontend
    source .venv_frontend/bin/activate
    pip install --upgrade pip wheel setuptools
    pip install -r requirements_frontend.txt
    deactivate
  '
}

patch_backend_and_frontend_config() {
  log "Patching backend and frontend config files"

  local backend_cfg="${PROJECT_DIR}/backend/cfg/config.py"
  local frontend_cfg="${PROJECT_DIR}/frontend/cfg/config.py"

  cp "${backend_cfg}" "${backend_cfg}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${frontend_cfg}" "${frontend_cfg}.bak.$(date +%Y%m%d%H%M%S)"

  sed -i "s|^\s*DB_HOST\s*=.*|    DB_HOST = \"${DB_HOST}\"|" "${backend_cfg}"
  sed -i "s|^\s*DB_PORT\s*=.*|    DB_PORT = ${DB_PORT}|" "${backend_cfg}"
  sed -i "s|^\s*DB_NAME\s*=.*|    DB_NAME = \"${DB_NAME}\"|" "${backend_cfg}"
  sed -i "s|^\s*DB_USERNAME\s*=.*|    DB_USERNAME = \"${DB_USERNAME}\"|" "${backend_cfg}"
  sed -i "s|^\s*DB_PASSWORD\s*=.*|    DB_PASSWORD = \"${DB_PASSWORD}\"|" "${backend_cfg}"
  sed -i "s|^\s*API_HOST\s*=.*|    API_HOST = \"${API_HOST}\"|" "${backend_cfg}"
  sed -i "s|^\s*API_PORT\s*=.*|    API_PORT = ${API_PORT}|" "${backend_cfg}"
  sed -i "s|^\s*URL_API\s*=.*|    URL_API = \"https://${DOMAIN_API}\"|" "${backend_cfg}"

  sed -i "s|^\s*URL_API\s*=.*|    URL_API = \"https://${DOMAIN_API}\"|" "${frontend_cfg}"
}

restore_database() {
  if [[ -f "${DB_RESTORE_FILE}" ]]; then
    log "Restoring DB from ${DB_RESTORE_FILE}"
    mysql -h localhost -u root -p"${DB_PASSWORD}" "${DB_NAME}" < "${DB_RESTORE_FILE}"
  else
    warn "Backup file not found: ${DB_RESTORE_FILE}"
    warn "To restore later, copy baseZD2703.sql and import manually."
  fi
}

prepare_runtime_logs() {
  log "Preparing runtime log files in ${LOG_DIR}"
  mkdir -p "${LOG_DIR}"
  touch "${BACKEND_LOG_FILE}" "${FRONTEND_LOG_FILE}"
  chown -R "${SERVER_USER}:${SERVER_GROUP}" "${LOG_DIR}"
  chmod 775 "${LOG_DIR}"
  chmod 664 "${BACKEND_LOG_FILE}" "${FRONTEND_LOG_FILE}"
}

create_systemd_services() {
  log "Creating systemd services"

  cat > /etc/systemd/system/zion-backend.service <<EOF
[Unit]
Description=Zion FastAPI Backend
After=network.target mysql.service
Wants=mysql.service

[Service]
User=${SERVER_USER}
Group=${SERVER_GROUP}
WorkingDirectory=${PROJECT_DIR}/backend
ExecStart=${PROJECT_DIR}/.venv_backend/bin/python run_backend.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:${BACKEND_LOG_FILE}
StandardError=append:${BACKEND_LOG_FILE}

[Install]
WantedBy=multi-user.target
EOF

  cat > /etc/systemd/system/zion-frontend.service <<EOF
[Unit]
Description=Zion Flet Frontend
After=network.target zion-backend.service
Wants=zion-backend.service

[Service]
User=${SERVER_USER}
Group=${SERVER_GROUP}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/.venv_frontend/bin/python app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:${FRONTEND_LOG_FILE}
StandardError=append:${FRONTEND_LOG_FILE}

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable zion-backend zion-frontend
  systemctl restart zion-backend zion-frontend
}

configure_nginx() {
  log "Configuring Nginx"

  cat > /etc/nginx/sites-available/${DOMAIN_API} <<EOF
server {
    listen 80;
    server_name ${DOMAIN_API};

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:${API_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF

  cat > /etc/nginx/sites-available/${DOMAIN_APP} <<EOF
server {
    listen 80;
    server_name ${DOMAIN_APP};

    location / {
        proxy_pass http://127.0.0.1:${FLET_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 120s;
    }
}
EOF

  ln -sf /etc/nginx/sites-available/${DOMAIN_API} /etc/nginx/sites-enabled/${DOMAIN_API}
  ln -sf /etc/nginx/sites-available/${DOMAIN_APP} /etc/nginx/sites-enabled/${DOMAIN_APP}
  rm -f /etc/nginx/sites-enabled/default

  nginx -t
  systemctl enable nginx
  systemctl restart nginx
}

enable_https() {
  if [[ "${ENABLE_HTTPS}" != "1" ]]; then
    warn "ENABLE_HTTPS=0, skipping certbot"
    return
  fi

  log "Installing certbot and issuing certificates"
  DEBIAN_FRONTEND=noninteractive apt -y install certbot python3-certbot-nginx

  certbot --nginx \
    --non-interactive \
    --agree-tos \
    -m "${CERTBOT_EMAIL}" \
    -d "${DOMAIN_API}" \
    -d "${DOMAIN_APP}" \
    --redirect

  certbot renew --dry-run
}

print_summary() {
  cat <<EOF

Installation complete.

Validation commands:
  systemctl status zion-backend --no-pager
  systemctl status zion-frontend --no-pager
  systemctl status nginx --no-pager

  curl -I http://127.0.0.1:${API_PORT}/health
  curl -I https://${DOMAIN_API}/health
  curl -I https://${DOMAIN_APP}/

Runtime logs (exceptions/errors):
  tail -f ${BACKEND_LOG_FILE}
  tail -f ${FRONTEND_LOG_FILE}
  journalctl -u zion-backend -f
  journalctl -u zion-frontend -f
  tail -f /var/log/nginx/error.log

EOF
}

main() {
  require_root
  require_vars
  apt_install_base
  configure_firewall
  install_mysql
  configure_mysql_root_and_schema
  configure_mysql_concurrency
  install_python_build_deps
  create_service_user
  install_pyenv_python
  checkout_project
  setup_virtualenvs_and_dependencies
  patch_backend_and_frontend_config
  restore_database
  prepare_runtime_logs
  create_systemd_services
  configure_nginx
  enable_https
  print_summary
}

main "$@"
