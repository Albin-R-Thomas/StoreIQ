#!/usr/bin/env bash
# Run with sudo after bootstrap: configure-host.sh HOSTNAME BACKUP_CONTAINER_URL
set -euo pipefail
hostname="${1:?hostname required}"
backup_url="${2:?private backup container URL required}"
[[ "$hostname" =~ ^[a-z0-9.-]+$ ]] || exit 1
[[ "$backup_url" =~ ^https://[a-z0-9]+\.blob\.core\.windows\.net/[a-z0-9-]+$ ]] || exit 1
printf 'server_names_hash_bucket_size 128;\n' >/etc/nginx/conf.d/storeiq-http.conf
cat >/etc/nginx/sites-available/storeiq <<EOF
server {
    listen 80;
    server_name $hostname;
    client_max_body_size 10m;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
        proxy_buffering off;
    }
}
EOF
ln -sfn /etc/nginx/sites-available/storeiq /etc/nginx/sites-enabled/storeiq
nginx -t
systemctl reload nginx
certbot --nginx --non-interactive --agree-tos --register-unsafely-without-email --redirect -d "$hostname"
install -d -m 0755 /opt/storeiq/bin
install -m 0755 "$(dirname "$0")/backup.py" /opt/storeiq/bin/backup.py
printf 'STOREIQ_BACKUP_URL=%s\n' "$backup_url" >/etc/storeiq-backup.conf
cat >/etc/systemd/system/storeiq-backup.service <<'EOF'
[Unit]
Description=Verify and upload StoreIQ SQLite backup
Wants=network-online.target
After=network-online.target docker.service
[Service]
Type=oneshot
User=azureuser
Group=azureuser
EnvironmentFile=/etc/storeiq-backup.conf
ExecStart=/usr/bin/python3 /opt/storeiq/bin/backup.py
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/storeiq/backups /opt/storeiq/data
EOF
cat >/etc/systemd/system/storeiq-backup.timer <<'EOF'
[Unit]
Description=Daily StoreIQ database backup
[Timer]
OnCalendar=*-*-* 02:30:00 UTC
Persistent=true
RandomizedDelaySec=300
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now storeiq-backup.timer
