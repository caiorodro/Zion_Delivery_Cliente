#!/usr/bin/env bash
# ==============================================================================
#  Zion Delivery Cliente – Instalador BeerVT – Ubuntu 24.04 LTS
#
#  O que este script faz (ordem de execução):
#   1.  Pacotes base do SO + firewall UFW
#   2.  MySQL 8 + senha root + schema 'zion' + tuning de concorrência
#   3.  Restaura backup da base de dados
#   4.  Cria usuário de serviço 'zion'
#   5.  Python 3.10.11 via pyenv
#   6.  Virtualenvs (.venv_backend / .venv_frontend) + dependências pip
#   7.  Ajusta configs da aplicação para produção
#   8.  Garante diretórios de log com permissões corretas
#   9.  Cria e ativa serviços systemd (zion-backend-beervt / zion-frontend-beervt)
#  10.  Configura Nginx como reverse proxy (HTTP)
#  11.  Emite certificados HTTPS via Let's Encrypt (Certbot)
#  12.  Validação pós-instalação e resumo
#
#  Pré-requisito obrigatório ANTES de rodar este script:
#  ──────────────────────────────────────────────────────
#  Transfira o backup SQL do Windows para o servidor:
#
#    # No PowerShell, na máquina Windows:
#    scp C:\Softwares\beerVT\baseDelivery.sql SEU_USUARIO@IP_DO_SERVIDOR:/opt/zion/
#
#  Transfira o código-fonte do projeto:
#
#    scp -r C:\Projetos\Zion_Delivery_Cliente SEU_USUARIO@IP_DO_SERVIDOR:/opt/zion/
#
#  Após os uploads, execute no servidor:
#
#    sudo bash /opt/zion/Zion_Delivery_Cliente/deploy/install_beervt_ubuntu24.sh
#
#  Variáveis opcionais que podem ser sobrescritas via env:
#    CERTBOT_EMAIL     – e-mail para o Let's Encrypt (padrão: infra@ziondelivery.app.br)
#    ENABLE_HTTPS      – 1 (padrão) emite certificado; 0 pula
#    MYSQL_MAX_CONNECTIONS, MYSQL_INNODB_BUFFER_POOL_SIZE, etc.
# ==============================================================================

set -Eeuo pipefail

# ─── Domínios ─────────────────────────────────────────────────────────────────
DOMAIN_API="servicebeervt.ziondelivery.app.br"
DOMAIN_APP="lojabeervt.ziondelivery.app.br"

# ─── Certbot ──────────────────────────────────────────────────────────────────
CERTBOT_EMAIL="${CERTBOT_EMAIL:-infra@ziondelivery.app.br}"
ENABLE_HTTPS="${ENABLE_HTTPS:-1}"

# ─── Usuário de serviço ───────────────────────────────────────────────────────
SERVER_USER="zion"
SERVER_GROUP="zion"

# ─── Caminhos ─────────────────────────────────────────────────────────────────
BASE_DIR="/opt/zion"
PROJECT_DIR="/opt/zion/Zion_Delivery_Cliente"

# ─── Banco de dados ───────────────────────────────────────────────────────────
DB_HOST="127.0.0.1"
DB_PORT="3306"
DB_NAME="zion"
DB_USERNAME="root"
DB_PASSWORD="56Runna01"

# Caminho esperado do backup no servidor (faça upload antes de rodar o script)
DB_BACKUP_FILE="/opt/zion/baseDelivery.sql"

# ─── Portas das aplicações ────────────────────────────────────────────────────
API_PORT="8000"
FLET_PORT="8080"

# ─── Logs ─────────────────────────────────────────────────────────────────────
# Backend exceptions → /tmp/errorLog.txt  (hardcoded em backend/base/error_logger.py)
# stdout/stderr do backend e frontend → journald (acessível via journalctl)
# Frontend app log   → ${PROJECT_DIR}/frontend/log/frontend.log  (RotatingFileHandler)
# Log desta instalação:
INSTALL_LOG="/tmp/zion_install_beervt.log"

# ─── Tuning MySQL (ajuste conforme a RAM disponível no servidor) ──────────────
MYSQL_MAX_CONNECTIONS="${MYSQL_MAX_CONNECTIONS:-300}"
MYSQL_INNODB_BUFFER_POOL_SIZE="${MYSQL_INNODB_BUFFER_POOL_SIZE:-2G}"
MYSQL_INNODB_BUFFER_POOL_INSTANCES="${MYSQL_INNODB_BUFFER_POOL_INSTANCES:-2}"
MYSQL_INNODB_LOG_FILE_SIZE="${MYSQL_INNODB_LOG_FILE_SIZE:-256M}"
MYSQL_THREAD_CACHE_SIZE="${MYSQL_THREAD_CACHE_SIZE:-50}"
MYSQL_TABLE_OPEN_CACHE="${MYSQL_TABLE_OPEN_CACHE:-2000}"
MYSQL_TABLE_DEFINITION_CACHE="${MYSQL_TABLE_DEFINITION_CACHE:-1000}"

# ==============================================================================
# Helpers
# ==============================================================================
log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]  $*" | tee -a "${INSTALL_LOG}"; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]  $*" | tee -a "${INSTALL_LOG}" >&2; }
die()  {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "${INSTALL_LOG}" >&2
  echo ""
  echo "  Consulte o log completo desta instalação em: ${INSTALL_LOG}"
  exit 1
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || \
    die "Execute como root:\n  sudo bash ${PROJECT_DIR}/deploy/install_beervt_ubuntu24.sh"
}

# ==============================================================================
# Etapa 0 – Verificações iniciais
# ==============================================================================
check_preconditions() {
  log "Verificando pré-condições..."

  # Backup SQL
  if [[ ! -f "${DB_BACKUP_FILE}" ]]; then
    die "Backup SQL não encontrado em '${DB_BACKUP_FILE}'.\n\
  Transfira o arquivo do Windows para o servidor antes de continuar:\n\
\n\
    # No PowerShell (máquina Windows):\n\
    scp C:\\Softwares\\beerVT\\baseDelivery.sql SEU_USUARIO@IP_SERVIDOR:/opt/zion/\n\
\n\
  Em seguida re-rode este script."
  fi
  log "  ✔  Backup SQL: ${DB_BACKUP_FILE}"

  # Projeto
  if [[ ! -d "${PROJECT_DIR}" ]]; then
    die "Projeto não encontrado em '${PROJECT_DIR}'.\n\
  Transfira o projeto do Windows:\n\
\n\
    # No PowerShell (máquina Windows):\n\
    scp -r C:\\Projetos\\Zion_Delivery_Cliente SEU_USUARIO@IP_SERVIDOR:/opt/zion/\n\
\n\
  Em seguida re-rode este script."
  fi
  log "  ✔  Projeto:     ${PROJECT_DIR}"
}

# ==============================================================================
# Etapa 1 – Pacotes base do SO e firewall
# ==============================================================================
apt_install_base() {
  log "═══ [1/12] Atualizando SO e instalando pacotes base ═══"
  apt-get update -q
  DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
  DEBIAN_FRONTEND=noninteractive apt-get -y install \
    git curl wget build-essential pkg-config software-properties-common \
    ca-certificates gnupg lsb-release ufw nginx certbot python3-certbot-nginx
}

configure_firewall() {
  log "Configurando UFW"
  ufw allow OpenSSH       || true
  ufw allow "Nginx Full"  || true
  ufw --force enable       || true
}

# ==============================================================================
# Etapa 2 – MySQL 8
# ==============================================================================
install_mysql() {
  log "═══ [2/12] Instalando MySQL 8 ═══"
  DEBIAN_FRONTEND=noninteractive apt-get -y install mysql-server
  systemctl enable mysql
  systemctl start mysql
}

configure_mysql() {
  log "Configurando credenciais root e schema '${DB_NAME}'"
  mysql --connect-expired-password <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS 'root'@'${DB_HOST}' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'${DB_HOST}' WITH GRANT OPTION;
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
FLUSH PRIVILEGES;
SQL
}

configure_mysql_concurrency() {
  log "Aplicando tuning de concorrência no MySQL"
  cat > /etc/mysql/mysql.conf.d/zzz-zion-tuning.cnf <<EOF
[mysqld]
# ── Conexões e cache de threads ───────────────────────────────────────────────
max_connections              = ${MYSQL_MAX_CONNECTIONS}
thread_cache_size            = ${MYSQL_THREAD_CACHE_SIZE}
table_open_cache             = ${MYSQL_TABLE_OPEN_CACHE}
table_definition_cache       = ${MYSQL_TABLE_DEFINITION_CACHE}
skip_name_resolve            = ON
performance_schema           = ON

# ── InnoDB ────────────────────────────────────────────────────────────────────
innodb_buffer_pool_size      = ${MYSQL_INNODB_BUFFER_POOL_SIZE}
innodb_buffer_pool_instances = ${MYSQL_INNODB_BUFFER_POOL_INSTANCES}
innodb_log_file_size         = ${MYSQL_INNODB_LOG_FILE_SIZE}
innodb_flush_log_at_trx_commit = 1
innodb_flush_method          = O_DIRECT

# ── Tabelas temporárias ───────────────────────────────────────────────────────
tmp_table_size               = 64M
max_heap_table_size          = 64M
EOF

  systemctl restart mysql
  log "  ✔  MySQL reiniciado com novo tuning"
}

# ==============================================================================
# Etapa 3 – Restaurar backup
# ==============================================================================
restore_database() {
  log "═══ [3/12] Restaurando backup em '${DB_NAME}' (pode demorar alguns minutos) ═══"
  mysql -u"${DB_USERNAME}" -p"${DB_PASSWORD}" "${DB_NAME}" < "${DB_BACKUP_FILE}"
  log "  ✔  Backup restaurado com sucesso"
}

# ==============================================================================
# Etapa 4 – Usuário de serviço
# ==============================================================================
create_service_user() {
  log "═══ [4/12] Configurando usuário de serviço '${SERVER_USER}' ═══"
  if id -u "${SERVER_USER}" >/dev/null 2>&1; then
    log "  ✔  Usuário '${SERVER_USER}' já existe"
  else
    useradd -m -s /bin/bash "${SERVER_USER}"
    log "  ✔  Usuário '${SERVER_USER}' criado"
  fi
}

# ==============================================================================
# Etapa 5 – Python 3.10.11 via pyenv
# ==============================================================================
install_python_build_deps() {
  log "═══ [5/12] Dependências de build do Python ═══"
  DEBIAN_FRONTEND=noninteractive apt-get -y install \
    make zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev libssl-dev
}

install_pyenv_python() {
  log "Instalando pyenv e Python 3.10.11 para o usuário '${SERVER_USER}'"
  su - "${SERVER_USER}" -c '
    if [[ ! -d "$HOME/.pyenv" ]]; then
      curl -fsSL https://pyenv.run | bash
    fi
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    pyenv install -s 3.10.11
    pyenv global 3.10.11
    python --version
  '
  log "  ✔  Python 3.10.11 instalado"
}

# ==============================================================================
# Etapa 6 – Virtualenvs e dependências pip
# ==============================================================================
setup_virtualenvs() {
  log "═══ [6/12] Criando virtualenvs e instalando dependências Python ═══"

  # Garante propriedade antes de criar os venvs
  chown -R "${SERVER_USER}:${SERVER_GROUP}" "${BASE_DIR}"

  su - "${SERVER_USER}" -c "
    export PATH=\"\$HOME/.pyenv/bin:\$PATH\"
    eval \"\$(pyenv init -)\"
    cd '${PROJECT_DIR}'

    # Backend
    python -m venv .venv_backend
    .venv_backend/bin/pip install --quiet --upgrade pip wheel setuptools
    .venv_backend/bin/pip install --quiet -r requirements_backend.txt
    echo '  ✔  .venv_backend OK'

    # Frontend
    python -m venv .venv_frontend
    .venv_frontend/bin/pip install --quiet --upgrade pip wheel setuptools
    .venv_frontend/bin/pip install --quiet -r requirements_frontend.txt
    echo '  ✔  .venv_frontend OK'
  "
}

# ==============================================================================
# Etapa 7 – Patching dos arquivos de configuração para produção
# ==============================================================================
patch_configs() {
  log "═══ [7/12] Atualizando configurações para produção ═══"

  # frontend/cfg/config.py → URL da API aponta para o domínio de produção
  sed -i \
    "s|URL_API = .*|URL_API = \"https://${DOMAIN_API}\"|g" \
    "${PROJECT_DIR}/frontend/cfg/config.py"
  log "  ✔  frontend/cfg/config.py: URL_API → https://${DOMAIN_API}"

  # backend/cfg/config.py → ProductionConfig já tem API_HOST = "0.0.0.0";
  # Garante que o Config base também escuta em todas as interfaces
  sed -i \
    's|API_HOST = "127.0.0.1"|API_HOST = "0.0.0.0"|g' \
    "${PROJECT_DIR}/backend/cfg/config.py" || true
  log "  ✔  backend/cfg/config.py: API_HOST → 0.0.0.0"
}

# ==============================================================================
# Etapa 8 – Diretórios de log
# ==============================================================================
prepare_log_dirs() {
  log "═══ [8/12] Preparando diretórios de log ═══"

  # Log do frontend (RotatingFileHandler em frontend/base/logging_setup.py)
  mkdir -p "${PROJECT_DIR}/frontend/log"
  chown -R "${SERVER_USER}:${SERVER_GROUP}" "${PROJECT_DIR}/frontend/log"
  chmod 775 "${PROJECT_DIR}/frontend/log"
  log "  ✔  Frontend log: ${PROJECT_DIR}/frontend/log/frontend.log"

  # Log de exceções do backend (hardcoded em backend/base/error_logger.py)
  touch /tmp/errorLog.txt
  chmod 664 /tmp/errorLog.txt
  log "  ✔  Backend exceptions: /tmp/errorLog.txt"

  # stdout/stderr → journald via serviços systemd
  log "  ✔  stdout/stderr → journald (journalctl -u zion-backend-beervt / -u zion-frontend-beervt)"
}

# ==============================================================================
# Etapa 9 – Serviços systemd
# ==============================================================================
create_backend_service() {
  log "═══ [9/12] Criando serviços systemd ═══"
  cat > /etc/systemd/system/zion-backend-beervt.service <<EOF
[Unit]
Description=Zion Delivery Backend – BeerVT (FastAPI / uvicorn)
Documentation=https://ziondelivery.app.br
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User=${SERVER_USER}
Group=${SERVER_GROUP}
WorkingDirectory=${PROJECT_DIR}/backend
Environment="PATH=/home/${SERVER_USER}/.pyenv/shims:/home/${SERVER_USER}/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${PROJECT_DIR}/.venv_backend/bin/python run_backend.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=zion-backend-beervt

[Install]
WantedBy=multi-user.target
EOF
  log "  ✔  zion-backend-beervt.service criado"
}

create_frontend_service() {
  cat > /etc/systemd/system/zion-frontend-beervt.service <<EOF
[Unit]
Description=Zion Delivery Frontend – BeerVT (Flet Web / porta ${FLET_PORT})
Documentation=https://ziondelivery.app.br
After=network.target zion-backend-beervt.service

[Service]
Type=simple
User=${SERVER_USER}
Group=${SERVER_GROUP}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=/home/${SERVER_USER}/.pyenv/shims:/home/${SERVER_USER}/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${PROJECT_DIR}/.venv_frontend/bin/python app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=zion-frontend-beervt

[Install]
WantedBy=multi-user.target
EOF
  log "  ✔  zion-frontend-beervt.service criado"
}

enable_services() {
  systemctl daemon-reload
  systemctl enable zion-backend-beervt zion-frontend-beervt
  systemctl restart zion-backend-beervt
  systemctl restart zion-frontend-beervt
  log "  ✔  Serviços ativados e iniciados"
}

# ==============================================================================
# Etapa 10 – Nginx (reverse proxy HTTP)
# ==============================================================================
configure_nginx() {
  log "═══ [10/12] Configurando Nginx ═══"

  # ── Backend – FastAPI ──────────────────────────────────────────────────────
  cat > /etc/nginx/sites-available/zion-backend-beervt <<EOF
server {
    listen 80;
    server_name ${DOMAIN_API};

    access_log /var/log/nginx/zion-backend-beervt_access.log;
    error_log  /var/log/nginx/zion-backend-beervt_error.log warn;

    # Aumenta limite para upload de imagens de produto
    client_max_body_size 10M;

    location / {
        proxy_pass         http://127.0.0.1:${API_PORT};
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
EOF

  # ── Frontend – Flet Web (WebSocket obrigatório) ────────────────────────────
  cat > /etc/nginx/sites-available/zion-frontend-beervt <<EOF
server {
    listen 80;
    server_name ${DOMAIN_APP};

    access_log /var/log/nginx/zion-frontend-beervt_access.log;
    error_log  /var/log/nginx/zion-frontend-beervt_error.log warn;

    location / {
        proxy_pass         http://127.0.0.1:${FLET_PORT};
        proxy_http_version 1.1;
        # WebSocket – obrigatório para o Flet funcionar
        proxy_set_header   Upgrade           \$http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
}
EOF

  # Ativa os sites e desativa o default
  ln -sf /etc/nginx/sites-available/zion-backend-beervt  /etc/nginx/sites-enabled/
  ln -sf /etc/nginx/sites-available/zion-frontend-beervt /etc/nginx/sites-enabled/
  rm -f /etc/nginx/sites-enabled/default || true

  nginx -t || die "Configuração do Nginx inválida – corrija antes de prosseguir"
  systemctl reload nginx
  log "  ✔  Nginx configurado para os dois subdomínios"
}

# ==============================================================================
# Etapa 11 – HTTPS via Let's Encrypt (Certbot)
# ==============================================================================
issue_https() {
  log "═══ [11/12] Emitindo certificados HTTPS ═══"

  if [[ "${ENABLE_HTTPS}" != "1" ]]; then
    warn "ENABLE_HTTPS=${ENABLE_HTTPS} – etapa de HTTPS pulada."
    warn "Para emitir depois: certbot --nginx --email ${CERTBOT_EMAIL} -d ${DOMAIN_API} -d ${DOMAIN_APP}"
    return
  fi

  [[ -n "${CERTBOT_EMAIL}" ]] || die "CERTBOT_EMAIL não está definido"

  certbot --nginx \
    --non-interactive \
    --agree-tos \
    --email "${CERTBOT_EMAIL}" \
    -d "${DOMAIN_API}" \
    -d "${DOMAIN_APP}" \
    --redirect

  log "  ✔  Certificados emitidos e redirecionamento HTTP→HTTPS ativo"
}

# ==============================================================================
# Etapa 12 – Validação e resumo
# ==============================================================================
post_install_validation() {
  log "═══ [12/12] Validação pós-instalação ═══"
  sleep 4   # aguarda os serviços subirem

  for svc in zion-backend-beervt zion-frontend-beervt nginx mysql; do
    if systemctl is-active --quiet "${svc}"; then
      log "  ✔  ${svc} está ativo"
    else
      warn "  ✘  ${svc} NÃO está ativo"
      warn "     Diagnóstico: journalctl -u ${svc} -n 50 --no-pager"
    fi
  done

  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 "http://127.0.0.1:${API_PORT}/health" 2>/dev/null || echo "ERR")
  if [[ "${HTTP_CODE}" == "200" ]]; then
    log "  ✔  Backend /health → HTTP 200"
  else
    warn "  ✘  Backend /health retornou '${HTTP_CODE}'"
    warn "     Diagnóstico: journalctl -u zion-backend-beervt -n 50 --no-pager"
  fi
}

print_summary() {
  log ""
  log "╔══════════════════════════════════════════════════════════════════╗"
  log "║          Instalação BeerVT concluída com sucesso!               ║"
  log "╠══════════════════════════════════════════════════════════════════╣"
  log "║  Backend  (FastAPI)  → https://${DOMAIN_API}  ║"
  log "║  Frontend (Flet Web) → https://${DOMAIN_APP}     ║"
  log "╠══════════════════════════════════════════════════════════════════╣"
  log "║  Monitoramento de logs                                          ║"
  log "║                                                                 ║"
  log "║  # Logs em tempo real das aplicações (stdout/stderr):           ║"
  log "║  journalctl -u zion-backend-beervt  -f                         ║"
  log "║  journalctl -u zion-frontend-beervt -f                         ║"
  log "║                                                                 ║"
  log "║  # Exceções do backend (append-only):                           ║"
  log "║  tail -f /tmp/errorLog.txt                                      ║"
  log "║                                                                 ║"
  log "║  # Log rotativo do frontend (RotatingFileHandler):              ║"
  log "║  tail -f ${PROJECT_DIR}/frontend/log/frontend.log              ║"
  log "║                                                                 ║"
  log "║  # Logs do Nginx:                                               ║"
  log "║  tail -f /var/log/nginx/zion-backend-beervt_error.log          ║"
  log "║  tail -f /var/log/nginx/zion-frontend-beervt_error.log         ║"
  log "║                                                                 ║"
  log "║  # Log completo desta instalação:                               ║"
  log "║  ${INSTALL_LOG}                            ║"
  log "╠══════════════════════════════════════════════════════════════════╣"
  log "║  Banco de dados                                                 ║"
  log "║  Host: ${DB_HOST}:${DB_PORT}   Schema: ${DB_NAME}                          ║"
  log "║  mysql -u root -p${DB_PASSWORD} ${DB_NAME}                          ║"
  log "╚══════════════════════════════════════════════════════════════════╝"
}

# ==============================================================================
# Execução principal
# ==============================================================================
main() {
  mkdir -p "$(dirname "${INSTALL_LOG}")"
  : > "${INSTALL_LOG}"
  exec > >(tee -a "${INSTALL_LOG}") 2>&1

  log "Iniciando instalação – $(date)"
  log "  Domínio backend:  ${DOMAIN_API}"
  log "  Domínio frontend: ${DOMAIN_APP}"
  log "  Projeto:          ${PROJECT_DIR}"
  log "  Backup SQL:       ${DB_BACKUP_FILE}"
  log ""

  require_root
  check_preconditions

  apt_install_base
  configure_firewall

  install_mysql
  configure_mysql
  configure_mysql_concurrency
  restore_database

  create_service_user
  install_python_build_deps
  install_pyenv_python

  setup_virtualenvs

  patch_configs
  prepare_log_dirs

  create_backend_service
  create_frontend_service
  enable_services

  configure_nginx
  issue_https

  post_install_validation
  print_summary
}

main "$@"
