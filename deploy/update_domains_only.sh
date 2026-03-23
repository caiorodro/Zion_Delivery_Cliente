#!/usr/bin/env bash
set -Eeuo pipefail

# Updates only domain-related configuration for an existing Zion deployment.
# Does NOT install packages, configure MySQL, or recreate services.

DOMAIN_API="${DOMAIN_API:-ziondelivery.app.br}"
DOMAIN_APP="${DOMAIN_APP:-loja.ziondelivery.app.br}"

PROJECT_DIR="${PROJECT_DIR:-/opt/zion/Zion_Delivery_Cliente}"
API_PORT="${API_PORT:-8000}"
FLET_PORT="${FLET_PORT:-8080}"

ENABLE_HTTPS="${ENABLE_HTTPS:-1}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

log() {
  echo "[INFO] $*"
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "Run as root: sudo bash deploy/update_domains_only.sh"
  fi
}

require_files() {
  [[ -f "${PROJECT_DIR}/backend/cfg/config.py" ]] || die "backend config not found in ${PROJECT_DIR}"
  [[ -f "${PROJECT_DIR}/frontend/cfg/config.py" ]] || die "frontend config not found in ${PROJECT_DIR}"
}

patch_project_configs() {
  log "Updating API URL in backend/frontend config files"

  local backend_cfg="${PROJECT_DIR}/backend/cfg/config.py"
  local frontend_cfg="${PROJECT_DIR}/frontend/cfg/config.py"

  cp "${backend_cfg}" "${backend_cfg}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${frontend_cfg}" "${frontend_cfg}.bak.$(date +%Y%m%d%H%M%S)"

  sed -i "s|^\s*URL_API\s*=.*|    URL_API = \"https://${DOMAIN_API}\"|" "${backend_cfg}"
  sed -i "s|^\s*URL_API\s*=.*|    URL_API = \"https://${DOMAIN_API}\"|" "${frontend_cfg}"
}

configure_nginx() {
  log "Writing Nginx virtual hosts for API and APP domains"

  cat > "/etc/nginx/sites-available/${DOMAIN_API}" <<EOF
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

  cat > "/etc/nginx/sites-available/${DOMAIN_APP}" <<EOF
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

  ln -sf "/etc/nginx/sites-available/${DOMAIN_API}" "/etc/nginx/sites-enabled/${DOMAIN_API}"
  ln -sf "/etc/nginx/sites-available/${DOMAIN_APP}" "/etc/nginx/sites-enabled/${DOMAIN_APP}"

  nginx -t
  systemctl reload nginx
}

enable_https_if_requested() {
  if [[ "${ENABLE_HTTPS}" != "1" ]]; then
    log "ENABLE_HTTPS=0: skipping certbot"
    return
  fi

  [[ -n "${CERTBOT_EMAIL}" ]] || die "CERTBOT_EMAIL is required when ENABLE_HTTPS=1"

  log "Issuing/updating certificates with certbot"
  certbot --nginx \
    --non-interactive \
    --agree-tos \
    -m "${CERTBOT_EMAIL}" \
    -d "${DOMAIN_API}" \
    -d "${DOMAIN_APP}" \
    --redirect

  certbot renew --dry-run
}

restart_apps() {
  log "Restarting app services to apply config changes"
  systemctl restart zion-backend || true
  systemctl restart zion-frontend || true
}

print_summary() {
  cat <<EOF

Domain update completed.

Validated endpoints (run manually):
  curl -I https://${DOMAIN_API}/health
  curl -I https://${DOMAIN_APP}/

Service checks:
  systemctl status zion-backend --no-pager
  systemctl status zion-frontend --no-pager
  systemctl status nginx --no-pager

EOF
}

main() {
  require_root
  require_files
  patch_project_configs
  configure_nginx
  enable_https_if_requested
  restart_apps
  print_summary
}

main "$@"
