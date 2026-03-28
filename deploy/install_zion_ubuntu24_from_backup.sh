#!/usr/bin/env bash
set -Eeuo pipefail

# Zion Delivery Cliente - Ubuntu 24.04 installer (from DB backup)
#
# This script performs:
# 1) MySQL installation and concurrency tuning
# 2) Python 3.10.11 installation (pyenv)
# 3) Backend + frontend dependency installation
# 4) DB restore from backup SQL
# 5) systemd services for FastAPI and Flet
# 6) Nginx reverse proxy for API and APP domains
# 7) HTTPS with certbot
# 8) Runtime logs in /tmp/zion_logs
#
# Default expected project path:
#   /opt/zion/Zion_Delivery_Cliente
#
# Default expected backup path:
#   /opt/zion/Zion_Delivery_Cliente/Softwares/baseZD2803.sql

############################
# Defaults (override via env)
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

DB_RESTORE_FILE="${DB_RESTORE_FILE:-${PROJECT_DIR}/Softwares/baseZD2803.sql}"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
FLET_PORT="${FLET_PORT:-8080}"

LOG_DIR="${LOG_DIR:-/tmp/zion_logs}"
BACKEND_LOG_FILE="${BACKEND_LOG_FILE:-${LOG_DIR}/backend.log}"
FRONTEND_LOG_FILE="${FRONTEND_LOG_FILE:-${LOG_DIR}/frontend.log}"
BACKEND_EXC_FILE="${BACKEND_EXC_FILE:-${LOG_DIR}/backend_exceptions.txt}"
INSTALL_LOG_FILE="${INSTALL_LOG_FILE:-${LOG_DIR}/install.log}"

# MySQL tuning defaults (balanced for moderate concurrency)
MYSQL_MAX_CONNECTIONS="${MYSQL_MAX_CONNECTIONS:-300}"
MYSQL_INNODB_BUFFER_POOL_SIZE="${MYSQL_INNODB_BUFFER_POOL_SIZE:-4G}"
MYSQL_INNODB_BUFFER_POOL_INSTANCES="${MYSQL_INNODB_BUFFER_POOL_INSTANCES:-4}"
MYSQL_INNODB_LOG_FILE_SIZE="${MYSQL_INNODB_LOG_FILE_SIZE:-512M}"
MYSQL_THREAD_CACHE_SIZE="${MYSQL_THREAD_CACHE_SIZE:-100}"
MYSQL_TABLE_OPEN_CACHE="${MYSQL_TABLE_OPEN_CACHE:-4000}"
MYSQL_TABLE_DEFINITION_CACHE="${MYSQL_TABLE_DEFINITION_CACHE:-2000}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

warn() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" >&2
}

die() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2
  exit 1
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "Execute como root: sudo bash deploy/install_zion_ubuntu24_from_backup.sh"
  fi
}

require_vars() {
  if [[ "${ENABLE_HTTPS}" == "1" ]] && [[ -z "${CERTBOT_EMAIL}" ]]; then
    die "CERTBOT_EMAIL é obrigatório quando ENABLE_HTTPS=1"
  fi
}

prepare_install_log() {
  mkdir -p "${LOG_DIR}"
  touch "${INSTALL_LOG_FILE}"
  chmod 664 "${INSTALL_LOG_FILE}" || true
  exec > >(tee -a "${INSTALL_LOG_FILE}") 2>&1
}

apt_install_base() {
  log "Atualizando SO e instalando pacotes base"
  apt update
  DEBIAN_FRONTEND=noninteractive apt -y upgrade
  DEBIAN_FRONTEND=noninteractive apt -y install \
    git curl wget build-essential pkg-config software-properties-common \
    ca-certificates gnupg lsb-release ufw nginx
}

configure_firewall() {
  log "Configurando firewall"
  ufw allow OpenSSH || true
  ufw allow "Nginx Full" || true
  ufw --force enable || true
}

install_mysql() {
  log "Instalando MySQL"
  DEBIAN_FRONTEND=noninteractive apt -y install mysql-server
  systemctl enable mysql
  systemctl start mysql
}

configure_mysql_root_and_schema() {
  log "Configurando root do MySQL e schema ${DB_NAME}"

  mysql <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
FLUSH PRIVILEGES;
SQL
}

configure_mysql_concurrency() {
  log "Aplicando tuning de concorrência no MySQL"

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
  log "Instalando dependências de build do Python"
  DEBIAN_FRONTEND=noninteractive apt -y install \
    make zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev libssl-dev
}

create_service_user() {
  if id -u "${SERVER_USER}" >/dev/null 2>&1; then
    log "Usuário ${SERVER_USER} já existe"
  else
    log "Criando usuário ${SERVER_USER}"
    useradd -m -s /bin/bash "${SERVER_USER}"
  fi
}

ensure_project_tree() {
  mkdir -p "${BASE_DIR}"

  if [[ -d "${PROJECT_DIR}" ]]; then
    log "Projeto já presente em ${PROJECT_DIR}"
  else
    if [[ -z "${GIT_REPO_URL}" ]]; then
      die "Projeto não encontrado em ${PROJECT_DIR}. Informe GIT_REPO_URL ou copie o projeto para esse caminho."
    fi

    log "Clonando repositório em ${PROJECT_DIR}"
    if [[ -n "${GIT_BRANCH}" ]]; then
      git clone --branch "${GIT_BRANCH}" "${GIT_REPO_URL}" "${PROJECT_DIR}"
    else
      git clone "${GIT_REPO_URL}" "${PROJECT_DIR}"
    fi
  fi

  chown -R "${SERVER_USER}:${SERVER_GROUP}" "${BASE_DIR}"
}

install_pyenv_python() {
  log "Instalando pyenv e Python 3.10.11"

  su - "${SERVER_USER}" -c 'if [[ ! -d "$HOME/.pyenv" ]]; then curl https://pyenv.run | bash; fi'

  su - "${SERVER_USER}" -c '
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    pyenv install -s 3.10.11
    pyenv global 3.10.11
  '
}

setup_virtualenvs_and_dependencies() {
  log "Criando venvs e instalando bibliotecas do projeto"

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

patch_project_config() {
  log "Ajustando config do backend/frontend"

  local backend_cfg="${PROJECT_DIR}/backend/cfg/config.py"
  local frontend_cfg="${PROJECT_DIR}/frontend/cfg/config.py"

  [[ -f "${backend_cfg}" ]] || die "Arquivo não encontrado: ${backend_cfg}"
  [[ -f "${frontend_cfg}" ]] || die "Arquivo não encontrado: ${frontend_cfg}"

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
  if [[ ! -f "${DB_RESTORE_FILE}" ]]; then
    warn "Arquivo de backup não encontrado: ${DB_RESTORE_FILE}"
    warn "Copie o backup (baseZD2803.sql) e rode novamente apenas esta etapa, se necessário."
    return
  fi

  log "Restaurando banco ${DB_NAME} a partir de ${DB_RESTORE_FILE}"
  mysql -h localhost -u root -p"${DB_PASSWORD}" "${DB_NAME}" < "${DB_RESTORE_FILE}"
}

prepare_runtime_logs() {
  log "Preparando logs em ${LOG_DIR}"
  mkdir -p "${LOG_DIR}"
  touch "${BACKEND_LOG_FILE}" "${FRONTEND_LOG_FILE}" "${BACKEND_EXC_FILE}"

  # O backend grava exceções em /tmp/errorLog.txt; criamos um link para centralizar em /tmp/zion_logs
  ln -sfn "${BACKEND_EXC_FILE}" /tmp/errorLog.txt

  chown -R "${SERVER_USER}:${SERVER_GROUP}" "${LOG_DIR}"
  chmod 775 "${LOG_DIR}"
  chmod 664 "${BACKEND_LOG_FILE}" "${FRONTEND_LOG_FILE}" "${BACKEND_EXC_FILE}"
}

create_systemd_services() {
  log "Criando serviços systemd"

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
  log "Configurando Nginx para API e frontend"

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
    warn "ENABLE_HTTPS=0, pulando certbot"
    return
  fi

  log "Instalando certbot e emitindo certificado"
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

Instalação finalizada.

Validações:
  systemctl status zion-backend --no-pager
  systemctl status zion-frontend --no-pager
  systemctl status nginx --no-pager

  curl -I http://127.0.0.1:${API_PORT}/health
  curl -I https://${DOMAIN_API}/health
  curl -I https://${DOMAIN_APP}/

Logs:
  tail -f ${BACKEND_LOG_FILE}
  tail -f ${FRONTEND_LOG_FILE}
  tail -f ${BACKEND_EXC_FILE}
  tail -f ${INSTALL_LOG_FILE}

Backup SQL esperado:
  ${DB_RESTORE_FILE}

EOF
}

main() {
  require_root
  require_vars
  prepare_install_log
  apt_install_base
  configure_firewall
  install_mysql
  configure_mysql_root_and_schema
  configure_mysql_concurrency
  install_python_build_deps
  create_service_user
  ensure_project_tree
  install_pyenv_python
  setup_virtualenvs_and_dependencies
  patch_project_config
  restore_database
  prepare_runtime_logs
  create_systemd_services
  configure_nginx
  enable_https
  print_summary
}

main "$@"
