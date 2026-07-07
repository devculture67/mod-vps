#!/bin/bash
# ============================================================
# rairu-kun MOD Entrypoint
# Handles systemd (if available) or supervisord fallback
# ============================================================

set -e

echo "🚀 Starting rairu-kun MOD..."

# Setup environment
export HOME=/root
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Start SSH
echo "🔐 Starting SSH..."
mkdir -p /run/sshd
/usr/sbin/sshd

# Start bore tunnels
if [ -n "$BORE_TOKEN" ]; then
    echo "🔗 Starting Bore tunnels..."
    
    # Start multiple bore tunnels for different ports
    ports=(22 5000 5001 8080 8888 9000)
    for port in "${ports[@]}"; do
        # Run bore in background
        bore -s ${BORE_SERVER}:${BORE_PORT} -p ${port} --no-tls-verify 2>/dev/null &
        sleep 1
    done
    
    echo "✅ Bore tunnels started"
else
    echo "⚠️  BORE_TOKEN not set - skipping bore tunnels"
fi

# Check if we can run systemd (needs --privileged)
if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
    echo "🔧 systemd detected - starting services..."
    
    # Reload systemd
    systemctl daemon-reload 2>/dev/null || true
    
    # Enable and start services
    for svc in ssh bot1 bot2; do
        if [ -f /etc/systemd/system/${svc}.service ]; then
            systemctl enable ${svc} 2>/dev/null || true
            systemctl start ${svc} 2>/dev/null || true
            echo "   Started: ${svc}"
        fi
    done
    
    # If systemd is working, exec it
    if systemctl is-system-running 2>/dev/null | grep -q "running\|degraded"; then
        echo "✅ systemd running"
        exec /sbin/init
    fi
fi

# Fallback to supervisord
echo "📦 Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf