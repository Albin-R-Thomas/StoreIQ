#!/usr/bin/env bash
# Run by cloud-init on the dedicated StoreIQ VM. Contains no credentials.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl nginx certbot python3-certbot-nginx python3 rsync
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker azureuser
install -d -o azureuser -g azureuser -m 0750 /opt/storeiq /opt/storeiq/releases /opt/storeiq/backups
install -d -o 1000 -g 1000 -m 0750 /opt/storeiq/data
systemctl enable --now docker nginx
touch /opt/storeiq/bootstrap-complete
