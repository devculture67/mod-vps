#!/bin/bash
# ============================================================
# Bore Multi-Tunnel Manager
# Creates multiple bore tunnels for different ports
# ============================================================

set -e

BORE_SERVER=${BORE_SERVER:-bore.pub}
BORE_PORT=${BORE_PORT:-3977}
BORE_TOKEN=${BORE_TOKEN:-}

# Port mapping: local_port:remote_name
# Format: "local_port:name:protocol"
declare -A TUNNELS=(
    [22]="ssh:tcp"
    [5000]="bot-webhook-1:http"
    [5001]="bot-webhook-2:http"
    [5002]="bot-webhook-3:http"
    [5003]="bot-webhook-4:http"
    [8080]="admin:http"
    [8888]="api:http"
    [9000]="extra:http"
)

LOG_FILE="/var/log/bore-tunnels.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

start_tunnel() {
    local local_port=$1
    local name=$2
    local protocol=$3
    
    if [ "$protocol" = "tcp" ]; then
        # TCP tunnel for SSH
        bore local "$local_port" --to "$BORE_SERVER:$BORE_PORT" &
    else
        # HTTP tunnel for webhooks
        bore local "$local_port" --to "$BORE_SERVER:$BORE_PORT" &
    fi
    
    local pid=$!
    echo $pid > "/var/run/bore-${name}.pid"
    log "Started tunnel: $name (local:$local_port -> $BORE_SERVER:$BORE_PORT) PID:$pid"
}

stop_tunnel() {
    local name=$1
    local pid_file="/var/run/bore-${name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            log "Stopped tunnel: $name (PID:$pid)"
        fi
        rm -f "$pid_file"
    fi
}

show_status() {
    echo "=== Bore Tunnel Status ==="
    for port in "${!TUNNELS[@]}"; do
        IFS=':' read -r name protocol <<< "${TUNNELS[$port]}"
        pid_file="/var/run/bore-${name}.pid"
        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file" 2>/dev/null)" 2>/dev/null; then
            echo "  ✓ $name (port $port) - RUNNING"
        else
            echo "  ✗ $name (port $port) - STOPPED"
        fi
    done
    echo ""
}

# Main
case "${1:-start}" in
    start)
        mkdir -p /var/run
        log "Starting Bore tunnels..."
        
        for port in "${!TUNNELS[@]}"; do
            IFS=':' read -r name protocol <<< "${TUNNELS[$port]}"
            start_tunnel "$port" "$name" "$protocol"
            sleep 0.5
        done
        
        log "All tunnels started. Waiting..."
        wait
        ;;
    stop)
        log "Stopping all Bore tunnels..."
        for port in "${!TUNNELS[@]}"; do
            IFS=':' read -r name protocol <<< "${TUNNELS[$port]}"
            stop_tunnel "$name"
        done
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac