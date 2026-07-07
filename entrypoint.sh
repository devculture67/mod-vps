#!/bin/bash
# ============================================================
# rairu-kun MOD Entrypoint (Fixed for Railway)
# ============================================================

export HOME=/root
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

BOT_PASSWORD="${BOT_PASSWORD:-rairukun2025}"
BORE_SERVER="${BORE_SERVER:-bore.pub}"
NTFY_TOPIC="${NTFY_TOPIC:-dhcl48-vps}"

echo "🚀 Starting rairu-kun MOD..."

mkdir -p /run/sshd /var/log/supervisor /var/log/bots /var/log/nginx \
         /data /var/www/html /var/run

# Set root password at runtime (not at build time)
echo "root:${BOT_PASSWORD}" | chpasswd
echo "🔑 Password set"

# Generate self-signed SSL cert
if [ ! -f /etc/letsencrypt/live/localhost/fullchain.pem ]; then
    mkdir -p /etc/letsencrypt/live/localhost
    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout /etc/letsencrypt/live/localhost/privkey.pem \
        -out /etc/letsencrypt/live/localhost/fullchain.pem \
        -days 365 -subj "/CN=localhost" 2>/dev/null
    echo "🔒 Self-signed cert generated"
fi

# Nginx htpasswd
if [ ! -f /etc/nginx/.htpasswd ]; then
    echo "admin:$(openssl passwd -apr1 "${BOT_PASSWORD}")" > /etc/nginx/.htpasswd
fi

# Nginx config fix for actual paths
sed -i "s|/etc/letsencrypt/live/example.com|/etc/letsencrypt/live/localhost|g" \
    /etc/nginx/sites-enabled/default 2>/dev/null || true

# Start SSH
echo "🔐 Starting SSH..."
/usr/sbin/sshd

# Test & start Nginx
echo "🌐 Starting Nginx..."
nginx -t 2>/dev/null && nginx || echo "⚠️  Nginx failed, continuing..."

# Start Redis
echo "🔴 Starting Redis..."
redis-server --daemonize yes --loglevel warning 2>/dev/null || true

# Start bore tunnels and capture SSH port
echo "🔗 Starting Bore SSH tunnel..."
bore local 22 --to "${BORE_SERVER}" > /tmp/bore_ssh.log 2>&1 &
BORE_PID=$!
sleep 4

SSH_PORT=$(grep -oP 'remote_port=\K[0-9]+' /tmp/bore_ssh.log 2>/dev/null | head -1)
if [ -z "$SSH_PORT" ]; then
    SSH_PORT=$(grep -oP 'listening at .*:\K[0-9]+' /tmp/bore_ssh.log 2>/dev/null | head -1)
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       VPS SSH Connection Info        ║"
echo "╠══════════════════════════════════════╣"
echo "║  ssh root@${BORE_SERVER} -p ${SSH_PORT}"
echo "║  Password: ${BOT_PASSWORD}"
echo "╚══════════════════════════════════════╝"
echo ""

# Start additional bore tunnels for web services
bore local 80 --to "${BORE_SERVER}" > /tmp/bore_80.log 2>&1 &
bore local 8080 --to "${BORE_SERVER}" > /tmp/bore_8080.log 2>&1 &
bore local 8888 --to "${BORE_SERVER}" > /tmp/bore_8888.log 2>&1 &

sleep 2

PORT_80=$(grep -oP 'remote_port=\K[0-9]+|listening at .*:\K[0-9]+' /tmp/bore_80.log 2>/dev/null | head -1)
PORT_8080=$(grep -oP 'remote_port=\K[0-9]+|listening at .*:\K[0-9]+' /tmp/bore_8080.log 2>/dev/null | head -1)
PORT_8888=$(grep -oP 'remote_port=\K[0-9]+|listening at .*:\K[0-9]+' /tmp/bore_8888.log 2>/dev/null | head -1)

# Send ntfy notification
echo "📣 Sending ntfy notification..."
curl -s -X POST "https://ntfy.sh/${NTFY_TOPIC}" \
    -H "Title: 🚀 VPS Online - rairu-kun MOD" \
    -H "Priority: high" \
    -H "Tags: computer,rocket" \
    -d "$(printf '✅ VPS Started!\n\n🔐 SSH:\nssh root@%s -p %s\nPassword: %s\n\n🌐 Web Ports:\nHTTP  → %s:%s\nAdmin → %s:%s\nAPI   → %s:%s\n\n⏰ Time: %s' \
        "${BORE_SERVER}" "${SSH_PORT}" "${BOT_PASSWORD}" \
        "${BORE_SERVER}" "${PORT_80}" \
        "${BORE_SERVER}" "${PORT_8080}" \
        "${BORE_SERVER}" "${PORT_8888}" \
        "$(date '+%Y-%m-%d %H:%M:%S %Z')")" \
    2>/dev/null && echo "✅ ntfy notification sent to ${NTFY_TOPIC}" || echo "⚠️  ntfy failed"

# Start supervisord (manages all remaining services)
echo "📦 Starting supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
