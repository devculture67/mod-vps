#!/bin/bash
# ============================================================
# rairu-kun MOD Entrypoint
# Starts: SSH, Nginx, Fail2ban, Prometheus, Grafana, Redis, Bore, Bots
# ============================================================

set -e

echo "🚀 Starting rairu-kun MOD Full Stack..."

# Setup environment
export HOME=/root
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Create required directories
mkdir -p /run/sshd /var/log/supervisor /var/log/bots /var/log/nginx /var/log/grafana /var/lib/prometheus /var/lib/grafana /data /var/www/certbot /etc/letsencrypt/live

# Generate self-signed cert for nginx (if no Let's Encrypt)
if [ ! -f /etc/letsencrypt/live/example.com/fullchain.pem ]; then
    mkdir -p /etc/letsencrypt/live/example.com
    openssl req -x509 -nodes -newkey rsa:2048 -keyout /etc/letsencrypt/live/example.com/privkey.pem \
        -out /etc/letsencrypt/live/example.com/fullchain.pem \
        -days 365 -subj "/CN=localhost" 2>/dev/null
fi

# Create htpasswd for nginx auth
if [ ! -f /etc/nginx/.htpasswd ] && [ -n "$BOT_PASSWORD" ]; then
    echo "admin:$(openssl passwd -apr1 "$BOT_PASSWORD")" > /etc/nginx/.htpasswd
fi

# Start SSH
echo "🔐 Starting SSH..."
/usr/sbin/sshd

# Start Nginx (test config first)
echo "🌐 Starting Nginx..."
nginx -t && nginx

# Start Fail2ban
echo "🛡️ Starting Fail2ban..."
fail2ban-server -f -b 2>/dev/null &

# Start Redis
echo "🔴 Starting Redis..."
redis-server --daemonize yes 2>/dev/null &

# Start Prometheus
echo "📊 Starting Prometheus..."
prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/var/lib/prometheus --web.enable-lifecycle > /var/log/supervisor/prometheus.log 2>&1 &

# Start Grafana
echo "📈 Starting Grafana..."
grafana-server --homepath=/usr/share/grafana cfg:default.paths.logs=/var/log/grafana cfg:default.paths.data=/var/lib/grafana > /var/log/supervisor/grafana.log 2>&1 &

# Start Bore tunnels
if [ -n "$BORE_TOKEN" ]; then
    echo "🔗 Starting Bore tunnels..."
    
    ports=(22 80 443 5000 5001 5002 5003 8080 8888 9000)
    for port in "${ports[@]}"; do
        bore -s ${BORE_SERVER}:${BORE_PORT} -p ${port} --no-tls-verify 2>/dev/null &
        sleep 0.3
    done
    
    echo "✅ Bore tunnels started"
else
    echo "⚠️  BORE_TOKEN not set - skipping bore tunnels"
fi

# Check if we can run systemd (needs --privileged)
if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
    echo "🔧 systemd detected - starting services..."
    
    systemctl daemon-reload 2>/dev/null || true
    
    for svc in ssh bore-tunnels bot1 bot2 bot3 bot4 webhook-manager monitoring nginx fail2ban prometheus grafana redis; do
        if [ -f /etc/systemd/system/${svc}.service ]; then
            systemctl enable ${svc} 2>/dev/null || true
            systemctl start ${svc} 2>/dev/null || true
            echo "   Started: ${svc}"
        fi
    done
    
    if systemctl is-system-running 2>/dev/null | grep -q "running\|degraded"; then
        echo "✅ systemd running"
        exec /sbin/init
    fi
fi

# Fallback to supervisord (recommended)
echo "📦 Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf