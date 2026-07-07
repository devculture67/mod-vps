#!/usr/bin/env python3
"""
Monitoring Script - checks services and restarts if needed
"""

import subprocess
import time
import psutil
import logging
import requests
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVICES = {
    'sshd': 22,
    'bot-1': 5000,
    'bot-2': 5001,
    'admin': 8080,
}

def check_port(port):
    """Check if port is listening"""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                return True
        return False
    except:
        return False

def check_http(url):
    """Check HTTP endpoint"""
    try:
        r = requests.get(url, timeout=5)
        return r.status_code == 200
    except:
        return False

def restart_service(name):
    """Restart via supervisorctl"""
    try:
        subprocess.run(['supervisorctl', 'restart', name], check=True)
        logger.info(f"Restarted {name}")
    except Exception as e:
        logger.error(f"Failed to restart {name}: {e}")

def main():
    logger.info("Monitor started")
    while True:
        for name, port in SERVICES.items():
            if name == 'sshd':
                ok = check_port(port)
            else:
                ok = check_http(f'http://localhost:{port}/health')
            
            if not ok:
                logger.warning(f"{name} on port {port} is DOWN!")
                restart_service(name)
            else:
                logger.debug(f"{name} OK")
        
        # System stats
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        if cpu > 90 or mem > 90:
            logger.warning(f"High resource: CPU={cpu}% MEM={mem}%")
        
        time.sleep(30)

if __name__ == '__main__':
    main()