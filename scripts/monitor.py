#!/usr/bin/env python3
"""
Monitoring Script - checks services and sends ntfy alerts
"""

import subprocess
import time
import logging
import requests
import os
import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

NTFY_TOPIC = os.environ.get('NTFY_TOPIC', 'dhcl48-vps')

SERVICES = {
    'sshd': 22,
    'nginx': 80,
    'redis': 6379,
}

def check_port(port):
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                return True
        return False
    except Exception:
        return False

def restart_service(name):
    try:
        subprocess.run(['supervisorctl', 'restart', name], check=True, timeout=10)
        logger.info(f"Restarted {name}")
        send_ntfy(f"⚠️ Service Restarted: {name}", f"Service {name} was down and has been restarted.")
    except Exception as e:
        logger.error(f"Failed to restart {name}: {e}")

def send_ntfy(title, message):
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            headers={"Title": title, "Tags": "warning"},
            data=message,
            timeout=5
        )
    except Exception:
        pass

def get_system_info():
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return f"CPU: {cpu}% | RAM: {mem.percent}% ({mem.used//1024//1024}MB/{mem.total//1024//1024}MB) | Disk: {disk.percent}%"
    except Exception:
        return "N/A"

def main():
    logger.info("Monitor started")
    check_count = 0

    while True:
        try:
            for name, port in SERVICES.items():
                if not check_port(port):
                    logger.warning(f"{name} on port {port} is DOWN!")
                    restart_service(name)

            # Send hourly status to ntfy
            check_count += 1
            if check_count % 60 == 0:
                info = get_system_info()
                send_ntfy("💻 VPS Status", f"✅ VPS is running\n{info}")

        except Exception as e:
            logger.error(f"Monitor error: {e}")

        time.sleep(60)

if __name__ == '__main__':
    main()
