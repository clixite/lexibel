#!/usr/bin/env bash
# Generate a .env file with secure random secrets for LexiBel production.
# Usage: bash scripts/gen-secrets.sh

set -euo pipefail

ENV_FILE="${1:-.env.prod}"

if [ -f "$ENV_FILE" ]; then
  echo "!! $ENV_FILE already exists. Delete it first or pass a different filename."
  exit 1
fi

POSTGRES_PASSWORD=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
OAUTH_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
SETTINGS_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
MINIO_PASSWORD=$(openssl rand -hex 16)
ADMIN_PASSWORD="LexiBel$(openssl rand -hex 4)!"

cat > "$ENV_FILE" << EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
SECRET_KEY=${SECRET_KEY}
OAUTH_ENCRYPTION_KEY=${OAUTH_KEY}
SETTINGS_ENCRYPTION_KEY=${SETTINGS_KEY}
MINIO_PASSWORD=${MINIO_PASSWORD}
BOOTSTRAP_ADMIN_EMAIL=admin@lexibel.be
BOOTSTRAP_ADMIN_PASSWORD=${ADMIN_PASSWORD}
CORS_ORIGINS=https://lexibel.clixite.cloud
EOF

echo "Secrets generated in $ENV_FILE"
echo "Admin login: admin@lexibel.be / ${ADMIN_PASSWORD}"
echo "IMPORTANT: change the admin password after first login!"
