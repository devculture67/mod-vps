# ============================================================
# RAIRU-KUN MOD — Full Stack Bot Gateway
# Multi-port with: Nginx, Fail2ban, Prometheus, Grafana, 4 Bots
# ============================================================
FROM debian:bullseye-slim

# Build args
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
    sudo git htop net-tools iptables iproute2 \
    # Process manager
    supervisor \
    # Web server
    nginx \
    # Security
    fail2ban \
    # Monitoring
    prometheus grafana \
    # Dev tools
    build-essential nodejs npm \
    # Database
    sqlite3 redis-server postgresql-client \
    # Network
    dnsutils \
    # Cleanup
    && apt clean && rm -rf /var/lib/apt/lists/*

# ---------- BORE CLIENT ----------
RUN wget -q https://github.com/ekzhang/bore/releases/latest/download/bore-linux-amd64 -O /usr/local/bin/bore \
    && chmod +x /usr/local/bin/bore

# ---------- NGINX ----------
COPY nginx/nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /var/www/certbot /etc/letsencrypt

# ---------- FAIL2BAN ----------
COPY fail2ban/jail.local /etc/fail2ban/jail.local
COPY fail2ban/nginx-bot-*.conf /etc/fail2ban/filter.d/

# ---------- PROMETHEUS ----------
COPY prometheus/prometheus.yml /etc/prometheus/prometheus.yml
RUN mkdir -p /etc/prometheus/rules /var/lib/prometheus

# ---------- GRAFANA ----------
COPY grafana/dashboards/ /var/lib/grafana/dashboards/
RUN mkdir -p /etc/grafana/provisioning/dashboards /etc/grafana/provisioning/datasources

# ---------- SSH CONFIG ----------
RUN mkdir /run/sshd 2>/dev/null; \
    echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config; \
    echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config; \
    echo "root:${BOT_PASSWORD}" | chpasswd"; \
    sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config

# ---------- PYTHON DEPENDENCIES ----------
RUN pip3 install --no-cache-dir \
    flask flask-cors gunicorn \
    requests beautifulsoup4 \
    python-telegram-bot pyTelegramBotAPI \
    redis paho-mqtt \
    psutil prometheus-client \
    && pip3 install --no-cache-dir prometheus-flask-exporter

# ---------- SUPERVISOR CONFIG ----------
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ---------- BOT SCRIPTS ----------
RUN mkdir -p /opt/bots /var/log/bots /var/run /data
COPY scripts/ /opt/scripts/
RUN chmod +x /opt/scripts/*.sh 2>/dev/null; \
    chmod +x /opt/scripts/*.py 2>/dev/null
COPY examples/ /opt/bots/examples/

# ---------- SYSTEMD UNITS ----------
COPY systemd/ /etc/systemd/system/
RUN systemctl enable ssh 2>/dev/null; true

# ---------- PORTS ----------
# Core services
EXPOSE 22 80 443 53 67 68
# Databases
EXPOSE 3306 5432 6379
# Monitoring
EXPOSE 9090 9091 9100 9113 9115 3000
# Bot webhooks
EXPOSE 5000 5001 5002 5003
# API & Admin
EXPOSE 8080 8888 9000

# ---------- ENTRYPOINT ----------
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]