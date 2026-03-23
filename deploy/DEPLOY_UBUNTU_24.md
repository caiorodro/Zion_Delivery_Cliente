# Zion Delivery - Deploy Ubuntu 24.04 LTS

This guide installs the full stack in a new Ubuntu 24.04 server:
- MySQL 8 with concurrency tuning
- Python 3.10.11
- FastAPI backend service
- Flet frontend service
- Nginx reverse proxy
- HTTPS certificate for ziondelivery.app.br and loja.ziondelivery.app.br

## 1. Prerequisites

1. Ubuntu 24.04 LTS server with sudo/root access.
2. DNS A record for ziondelivery.app.br pointing to this server IP.
3. DNS A record for loja.ziondelivery.app.br pointing to this server IP.
4. Git repository URL for this project.
5. Email for Lets Encrypt certificate issuance.

## 2. Copy the installer to the server

If this repository is already on the server:

```bash
cd /opt/zion/Zion_Delivery_Cliente
chmod +x deploy/install_zion_ubuntu24.sh
```

If not, clone first and then run from repository root.

## 3. Run installer with required environment variables

Mandatory variables:
- GIT_REPO_URL
- DB_APP_PASSWORD
- CERTBOT_EMAIL (required when ENABLE_HTTPS=1)

Recommended command:

```bash
sudo env \
  GIT_REPO_URL="https://github.com/ORG/REPO.git" \
  DB_APP_PASSWORD="CHANGE_THIS_STRONG_PASSWORD" \
  CERTBOT_EMAIL="infra@ziondelivery.app.br" \
   DOMAIN_API="ziondelivery.app.br" \
   DOMAIN_APP="loja.ziondelivery.app.br" \
  ENABLE_HTTPS="1" \
  bash deploy/install_zion_ubuntu24.sh
```

If you omit `GIT_BRANCH`, the script clones the repository default branch automatically.
If you want to force a specific branch, pass it explicitly, for example `GIT_BRANCH="master"`.

## 4. What the script does

1. Updates OS packages.
2. Installs and configures MySQL 8.
3. Applies MySQL tuning in /etc/mysql/mysql.conf.d/zzz-zion-tuning.cnf.
4. Creates database zion and app user zion_app.
5. Installs Python build dependencies.
6. Installs pyenv and Python 3.10.11 for user zion.
7. Clones or updates the project in /opt/zion/Zion_Delivery_Cliente.
8. Creates virtual environments:
   - .venv_backend
   - .venv_frontend
9. Installs dependencies from:
   - requirements_backend.txt
   - requirements_frontend.txt
10. Patches project config files:
   - backend/cfg/config.py
   - frontend/cfg/config.py
11. Runs SQL migration:
   - backend/migrations/create_tables.sql
12. Creates and starts systemd services:
   - zion-backend.service
   - zion-frontend.service
13. Configures Nginx with two virtual hosts:
   - API on ziondelivery.app.br
   - Flet app on loja.ziondelivery.app.br
14. Issues HTTPS certificate with certbot and enables redirect HTTP -> HTTPS.

## 5. Post-install validation

```bash
systemctl status zion-backend --no-pager
systemctl status zion-frontend --no-pager
systemctl status nginx --no-pager

curl -I http://127.0.0.1:8000/health
curl -I https://ziondelivery.app.br/health
curl -I https://loja.ziondelivery.app.br/
```

Expected:
- backend health endpoint returns HTTP 200
- domain endpoint returns HTTPS response

## 6. Useful logs

```bash
journalctl -u zion-backend -f
journalctl -u zion-frontend -f
tail -f /var/log/nginx/error.log
```

## 7. Important production notes

1. The installer updates backend/cfg/config.py directly. For stronger security, move secrets to environment variables and read them in code.
2. Keep DB_APP_PASSWORD strong and unique.
3. Keep Ubuntu packages updated regularly.
4. Add automated MySQL backups (daily).
5. Use monitoring for CPU, RAM, disk, and process restarts.

## 8. Customization examples

Disable HTTPS creation in first run:

```bash
sudo env \
  GIT_REPO_URL="https://github.com/ORG/REPO.git" \
  DB_APP_PASSWORD="CHANGE_THIS" \
   DOMAIN_API="ziondelivery.app.br" \
   DOMAIN_APP="loja.ziondelivery.app.br" \
  ENABLE_HTTPS="0" \
  bash deploy/install_zion_ubuntu24.sh
```

Tune MySQL max connections:

```bash
sudo env \
  GIT_REPO_URL="https://github.com/ORG/REPO.git" \
  DB_APP_PASSWORD="CHANGE_THIS" \
  CERTBOT_EMAIL="infra@ziondelivery.app.br" \
   DOMAIN_API="ziondelivery.app.br" \
   DOMAIN_APP="loja.ziondelivery.app.br" \
  MYSQL_MAX_CONNECTIONS="500" \
  bash deploy/install_zion_ubuntu24.sh
```
