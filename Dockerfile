FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Jakarta \
    BOT_PASSWORD=rairukun2025 \
    BORE_SERVER=bore.pub \
    NTFY_TOPIC=dhcl48-vps

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    openssh-server \
    wget curl vim sudo git htop net-tools \
    supervisor \
    nginx \
    redis-server \
    python3 python3-pip \
    sqlite3 \
    dnsutils openssl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    flask flask-cors gunicorn \
    requests psutil

RUN wget -q https://github.com/ekzhang/bore/releases/download/v0.5.1/bore-v0.5.1-x86_64-unknown-linux-musl.tar.gz \
    -O /tmp/bore.tar.gz \
    && tar -xzf /tmp/bore.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/bore \
    && rm /tmp/bore.tar.gz

RUN mkdir -p /run/sshd \
    && echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config \
    && echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config \
    && sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config

COPY nginx/nginx.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default \
    && rm -f /etc/nginx/sites-enabled/default 2>/dev/null; \
    cp /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY scripts/ /opt/scripts/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chmod +x /opt/scripts/*.sh 2>/dev/null || true

RUN mkdir -p /var/log/supervisor /var/log/bots /data /var/www/html \
    /etc/letsencrypt/live/localhost

EXPOSE 22 80 443 5000 5001 8080 8888 9000

CMD ["/entrypoint.sh"]
