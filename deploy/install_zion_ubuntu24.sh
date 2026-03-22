#!/usr/bin/env bash
set -Eeuo pipefail

# Zion Delivery installer for Ubuntu 24.04 LTS
# - Installs MySQL 8 and applies concurrency tuning
# - Installs Python 3.10.11 via pyenv
# - Installs backend/frontend Python dependencies
# - Configures systemd services
# - Configures Nginx reverse proxy
# - Optionally enables HTTPS via certbot

############################
# User-configurable options
############################
DOMAIN="${DOMAIN:-ziondelivery.app.br}"
DOMAIN_WWW="${DOMAIN_WWW:-www.ziondelivery.app.br}"
SERVER_USER="${SERVER_USER:-zion}"
SERVER_GROUP="${SERVER_GROUP:-zion}"
BASE_DIR="${BASE_DIR:-/opt/zion}"
PROJECT_DIR="${PROJECT_DIR:-/opt/zion/Zion_Delivery_Cliente}"
GIT_REPO_URL="${GIT_REPO_URL:-}"
GIT_BRANCH="${GIT_BRANCH:-main}"

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-zion}"
DB_APP_USER="${DB_APP_USER:-zion_app}"
DB_APP_PASSWORD="${DB_APP_PASSWORD:-}"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
FLET_PORT="${FLET_PORT:-8080}"

ENABLE_HTTPS="${ENABLE_HTTPS:-1}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

# MySQL tuning defaults (good starting point for 8 GB RAM)
MYSQL_MAX_CONNECTIONS="${MYSQL_MAX_CONNECTIONS:-300}"
MYSQL_INNODB_BUFFER_POOL_SIZE="${MYSQL_INNODB_BUFFER_POOL_SIZE:-4G}"
MYSQL_INNODB_BUFFER_POOL_INSTANCES="${MYSQL_INNODB_BUFFER_POOL_INSTANCES:-4}"
MYSQL_INNODB_LOG_FILE_SIZE="${MYSQL_INNODB_LOG_FILE_SIZE:-512M}"
MYSQL_THREAD_CACHE_SIZE="${MYSQL_THREAD_CACHE_SIZE:-100}"
MYSQL_TABLE_OPEN_CACHE="${MYSQL_TABLE_OPEN_CACHE:-4000}"
MYSQL_TABLE_DEFINITION_CACHE="${MYSQL_TABLE_DEFINITION_CACHE:-2000}"

############################
# Helpers
############################
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
    die "Run this script as root: sudo bash deploy/install_zion_ubuntu24.sh"
  fi
}

require_vars() {
  [[ -n "${GIT_REPO_URL}" ]] || die "GIT_REPO_URL is required."
  [[ -n "${DB_APP_PASSWORD}" ]] || die "DB_APP_PASSWORD is required."
  if [[ "${ENABLE_HTTPS}" == "1" ]]; then
    [[ -n "${CERTBOT_EMAIL}" ]] || die "CERTBOT_EMAIL is required when ENABLE_HTTPS=1."
  fi
}

apt_install_base() {
  log "Updating apt and installing base packages"
  apt update
  DEBIAN_FRONTEND=noninteractive apt -y upgrade
  DEBIAN_FRONTEND=noninteractive apt -y install \
    git curl wget build-essential pkg-config software-properties-common \
    ca-certificates gnupg lsb-release ufw nginx
}

configure_firewall() {
  log "Configuring UFW"
  ufw allow OpenSSH || true
  ufw allow "Nginx Full" || true
  ufw --force enable || true
}

install_mysql() {
  log "Installing MySQL server"
  DEBIAN_FRONTEND=noninteractive apt -y install mysql-server
  systemctl enable mysql
  systemctl start mysql
}

configure_mysql_schema_and_user() {
  log "Creating MySQL database and application user"
  mysql <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS '${DB_APP_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_APP_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_APP_USER}'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL
}

configure_mysql_concurrency() {
  log "Applying MySQL concurrency tuning"
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
  log "Installing pyenv for ${SERVER_USER}"
  su - "${SERVER_USER}" -c 'if [[ ! -d "$HOME/.pyenv" ]]; then curl https://pyenv.run | bash; fi'

  log "Installing Python 3.10.11 via pyenv"
  su - "${SERVER_USER}" -c 'export PATH="$HOME/.pyenv/bin:$PATH"; eval "$(pyenv init -)"; pyenv install -s 3.10.11; pyenv global 3.10.11'
}

checkout_project() {
  log "Cloning or updating project"
  mkdir -p "${BASE_DIR}"
  chown -R "${SERVER_USER}:${SERVER_GROUP}" "${BASE_DIR}"

  if [[ -d "${PROJECT_DIR}/.git" ]]; then
    su - "${SERVER_USER}" -c "cd '${PROJECT_DIR}' && git fetch --all && git checkout '${GIT_BRANCH}' && git pull --ff-only"
  else
    su - "${SERVER_USER}" -c "cd '${BASE_DIR}' && git clone --branch '${GIT_BRANCH}' '${GIT_REPO_URL}' 'Zion_Delivery_Cliente'"
  fi
}

setup_virtualenvs_and_requirements() {
  log "Creating virtual environments and installing Python dependencies"
  su - "${SERVER_USER}" -c '
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    cd "'"${PROJECT_DIR}"'"

    python -m venv .venv_backend
    source .venv_backend/bin/activate
    pip install --upgrade pip wheel
    pip install -r requirements_backend.txt
    deactivate

    python -m venv .venv_frontend
    source .venv_frontend/bin/activate
    pip install --upgrade pip wheel
    pip install -r requirements_frontend.txt
    deactivate
  '
}

patch_project_configs() {
  log "Patching backend and frontend config files"

  local backend_cfg="${PROJECT_DIR}/backend/cfg/config.py"
  local frontend_cfg="${PROJECT_DIR}/frontend/cfg/config.py"

  cp "${backend_cfg}" "${backend_cfg}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${frontend_cfg}" "${frontend_cfg}.bak.$(date +%Y%m%d%H%M%S)"

  sed -i "s|^\s*DB_HOST\s*=.*|    DB_HOST = \"${DB_HOST}\"|" "${backend_cfg}"
  sed -i "s|^\s*DB_PORT\s*=.*|    DB_PORT = ${DB_PORT}|" "${backend_cfg}"
  sed -i "s|^\s*DB_NAME\s*=.*|    DB_NAME = \"${DB_NAME}\"|" "${backend_cfg}"
  sed -i "s|^\s*DB_USERNAME\s*=.*|    DB_USERNAME = \"${DB_APP_USER}\"|" "${backend_cfg}"
  sed -i "s|^\s*DB_PASSWORD\s*=.*|    DB_PASSWORD = \"${DB_APP_PASSWORD}\"|" "${backend_cfg}"
  sed -i "s|^\s*API_HOST\s*=.*|    API_HOST = \"${API_HOST}\"|" "${backend_cfg}"
  sed -i "s|^\s*API_PORT\s*=.*|    API_PORT = ${API_PORT}|" "${backend_cfg}"
  sed -i "s|^\s*URL_API\s*=.*|    URL_API = \"https://${DOMAIN}/api\"|" "${backend_cfg}"

  sed -i "s|^\s*URL_API\s*=.*|    URL_API = \"https://${DOMAIN}/api\"|" "${frontend_cfg}"
}

run_migrations() {
  log "Running SQL migration script"
  mysql "${DB_NAME}" < "${PROJECT_DIR}/backend/migrations/create_tables.sql"
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

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable zion-backend zion-frontend
  systemctl restart zion-backend zion-frontend
}

configure_nginx() {
  log "Configuring Nginx reverse proxy"

  cat > /etc/nginx/sites-available/${DOMAIN} <<EOF
server {
    listen 80;
    server_name ${DOMAIN} ${DOMAIN_WWW};

    client_max_body_size 20m;

    location /api/ {
        proxy_pass http://127.0.0.1:${API_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

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

  ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/${DOMAIN}
  rm -f /etc/nginx/sites-enabled/default

  nginx -t
  systemctl enable nginx
  systemctl restart nginx
}

enable_https_certbot() {
  if [[ "${ENABLE_HTTPS}" != "1" ]]; then
    warn "ENABLE_HTTPS=0, skipping certbot"
    return
  fi

  log "Installing certbot and issuing certificate"
  DEBIAN_FRONTEND=noninteractive apt -y install certbot python3-certbot-nginx

  certbot --nginx \
    --non-interactive \
    --agree-tos \
    -m "${CERTBOT_EMAIL}" \
    -d "${DOMAIN}" \
    -d "${DOMAIN_WWW}" \
    --redirect

  certbot renew --dry-run
}

print_validation() {
  cat <<EOF

Installation completed.

Validation commands:
  systemctl status zion-backend --no-pager
  systemctl status zion-frontend --no-pager
  systemctl status nginx --no-pager

  curl -I http://127.0.0.1:${API_PORT}/health
  curl -I https://${DOMAIN}/api/health
  curl -I https://${DOMAIN}/

Useful logs:
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
  configure_mysql_schema_and_user
  configure_mysql_concurrency
  install_python_build_deps
  create_service_user
  install_pyenv_python
  checkout_project
  setup_virtualenvs_and_requirements
  patch_project_configs
  run_migrations
  create_systemd_services
  configure_nginx
  enable_https_certbot
  print_validation
}

main "$@"
