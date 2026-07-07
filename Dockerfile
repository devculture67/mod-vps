# ============================================================
# RAIRU-KUN MOD — Multi-Port Bot Gateway with systemd support
# Original: craxid/rairu-kun
# Mod: Supervisord + Bore multi-tunnel + Bot deps
# ============================================================
FROM debian:bullseye-slim

ARG BORE_TOKEN
ARG BORE_SERVER=bore.pub
ARG BORE_PORT=3977
ARG REGION=ap
ARG BOT_PASSWORD=rairukun2025

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Jakarta
ENV BORE_TOKEN=${BORE_TOKEN}
ENV BORE_SERVER=${BORE_SERVER}
ENV BORE_PORT=${BORE_PORT}
ENV REGION=${REGION}
ENV BOT_PASSWORD=${BOT_PASSWORD}

# ---------- BASE SYSTEM ----------
RUN apt update && apt upgrade -y && apt install -y \
    # System
    systemd systemd-sysv \
    ssh wget unzip vim curl python3 python3-pip \
    sudo git htop net-tools iptables \
    # Process manager
    supervisor \
    # Dev tools
    build-essential nodejs npm \
    # Database (optional)
    sqlite3 \
    # Network
    dnsutils iproute2 \
    # Cleanup
    && apt clean && rm -rf /var/lib/apt/lists/*

# ---------- BORE CLIENT ----------
# Install bore via cargo (Rust) or download binary
RUN wget -q https://github.com/ekzhang/bore/releases/latest/download/bore-linux-amd64 -O /usr/local/bin/bore \
    && chmod +x /usr/local/bin/bore

# ---------- SSH CONFIG ----------
RUN mkdir /run/sshd 2>/dev/null; \
    echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config; \
    echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config; \
    echo "root:${BOT_PASSWORD}" | chpasswd; \
    sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config

# ---------- BOT DEPENDENCIES ----------
RUN pip3 install --no-cache-dir \
    flask flask-cors gunicorn \
    requests beautifulsoup4 \
    python-telegram-bot pyTelegramBotAPI \
    redis paho-mqtt \
    psutil

# ---------- BORE MULTI-TUNNEL SCRIPT ----------
COPY bore_tunnels.sh /opt/scripts/bore_tunnels.sh
RUN chmod +x /opt/scripts/bore_tunnels.sh

# ---------- SUPERVISOR CONFIG ----------
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ---------- BOT SCRIPTS ----------
RUN mkdir -p /opt/bots /var/log/bots
COPY scripts/ /opt/scripts/
RUN chmod +x /opt/scripts/*.sh 2>/dev/null; \
    chmod +x /opt/scripts/*.py 2>/dev/null
COPY examples/ /opt/bots/examples/

# ---------- SYSTEMD UNITS ----------
COPY systemd/ /etc/systemd/system/
RUN systemctl enable ssh 2>/dev/null; true

# ---------- PORTS ----------
# SSH | HTTP | HTTPS | MySQL | PostgreSQL
EXPOSE 22 80 443 3306 5432
# Bot webhooks | Custom services
EXPOSE 5000 5001 5002 5003 8080 8443 8888 9000

# ---------- ENTRYPOINT ----------
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]