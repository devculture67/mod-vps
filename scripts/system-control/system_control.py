#!/usr/bin/env python3
"""
System Control Bot - Manage services via Telegram & HTTP API
Features: restart services, view logs, execute commands, system info
"""

import os
import sys
import json
import subprocess
import psutil
import time
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN_4', os.getenv('BOT_TOKEN_1', 'YOUR_BOT_TOKEN'))
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
BOT_PASSWORD = os.getenv('BOT_PASSWORD', 'rairukun2025')
AUTHORIZED_USERS = set(filter(None, os.getenv('AUTHORIZED_USERS', '').split(',')))

# Services managed by supervisord
SERVICES = {
    'sshd': 'SSH Server',
    'bore-tunnels': 'Bore Tunnels',
    'bot-1': 'Bot 1 (Webhook)',
    'bot-2': 'Bot 2 (API)',
    'bot-3': 'Bot 3 (File Manager)',
    'bot-4': 'Bot 4 (System Control)',
    'flask-api': 'Flask Admin API',
    'monitoring': 'Monitoring Script',
}

def check_auth(chat_id):
    if AUTHORIZED_USERS and str(chat_id) not in AUTHORIZED_USERS:
        return False
    return True

def send_message(chat_id, text, parse_mode='Markdown'):
    requests.post(f'{API_URL}/sendMessage', json={
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }, timeout=10)

def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Timeout'
    except Exception as e:
        return -1, '', str(e)

# ============================================================
# HTTP API ENDPOINTS
# ============================================================

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'system-control'})

@app.route('/api/service/list', methods=['POST'])
def api_service_list():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    results = {}
    for svc, desc in SERVICES.items():
        code, out, err = run_cmd(f'supervisorctl status {svc}')
        if 'RUNNING' in out:
            status = 'running'
        elif 'STOPPED' in out:
            status = 'stopped'
        elif 'FATAL' in out:
            status = 'fatal'
        else:
            status = 'unknown'
        
        results[svc] = {
            'description': desc,
            'status': status,
            'raw': out.strip()
        }
    
    return jsonify(results)

@app.route('/api/service/action', methods=['POST'])
def api_service_action():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    svc = data.get('service')
    action = data.get('action')  # start, stop, restart, status
    
    if svc not in SERVICES:
        return jsonify({'error': 'Invalid service'}), 400
    
    if action not in ['start', 'stop', 'restart', 'status']:
        return jsonify({'error': 'Invalid action'}), 400
    
    code, out, err = run_cmd(f'supervisorctl {action} {svc}')
    return jsonify({
        'service': svc,
        'action': action,
        'success': code == 0,
        'output': out.strip(),
        'error': err.strip()
    })

@app.route('/api/service/logs', methods=['POST'])
def api_service_logs():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    svc = data.get('service')
    lines = int(data.get('lines', 100))
    
    if svc not in SERVICES:
        return jsonify({'error': 'Invalid service'}), 400
    
    # Get log file path from supervisor
    log_map = {
        'sshd': '/var/log/supervisor/sshd.log',
        'bore-tunnels': '/var/log/supervisor/bore.log',
        'bot-1': '/var/log/bots/bot1.log',
        'bot-2': '/var/log/bots/bot2.log',
        'bot-3': '/var/log/bots/bot3.log',
        'bot-4': '/var/log/bots/bot4.log',
        'flask-api': '/var/log/bots/flask.log',
        'monitoring': '/var/log/bots/monitor.log',
    }
    
    log_file = log_map.get(svc)
    if not log_file or not os.path.exists(log_file):
        return jsonify({'error': 'Log file not found'}), 404
    
    code, out, err = run_cmd(f'tail -n {lines} {log_file}')
    return jsonify({
        'service': svc,
        'lines': lines,
        'logs': out.strip().split('\n') if out else []
    })

@app.route('/api/system/info', methods=['POST'])
def api_system_info():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    return jsonify({
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': psutil.virtual_memory()._asdict(),
        'disk': psutil.disk_usage('/')._asdict(),
        'network': psutil.net_io_counters()._asdict(),
        'boot_time': psutil.boot_time(),
        'process_count': len(psutil.pids()),
        'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
    })

@app.route('/api/exec', methods=['POST'])
def api_exec():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    cmd = data.get('cmd', '')
    timeout = int(data.get('timeout', 30))
    
    if not cmd:
        return jsonify({'error': 'No command'}), 400
    
    code, out, err = run_cmd(cmd, timeout)
    return jsonify({
        'command': cmd,
        'returncode': code,
        'stdout': out[-5000:],  # Limit output
        'stderr': err[-5000:]
    })

# ============================================================
# TELEGRAM BOT HANDLERS
# ============================================================

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or 'message' not in data:
        return 'OK'
    
    msg = data['message']
    chat_id = msg['chat']['id']
    text = msg.get('text', '')
    
    if not check_auth(chat_id):
        send_message(chat_id, '❌ Unauthorized')
        return 'OK'
    
    parts = text.split(maxsplit=2)
    cmd = parts[0].lower() if parts else ''
    
    try:
        if cmd == '/start':
            send_message(chat_id,
                '🖥️ *System Control Bot*\n\n'
                'Commands:\n'
                '`/services` - List all services\n'
                '`/status <service>` - Service status\n'
                '`/restart <service>` - Restart service\n'
                '`/stop <service>` - Stop service\n'
                '`/start <service>` - Start service\n'
                '`/logs <service> [lines]` - View logs\n'
                '`/sysinfo` - System info\n'
                '`/exec <command>` - Execute command\n'
                '`/help` - Show this help')
        
        elif cmd == '/services':
            code, out, err = run_cmd('supervisorctl status')
            send_message(chat_id, f'📋 *Services*\n```\n{out or "No services"}\n```')
        
        elif cmd == '/status':
            if len(parts) < 2:
                send_message(chat_id, 'Usage: `/status <service>`')
                return 'OK'
            svc = parts[1]
            if svc not in SERVICES:
                send_message(chat_id, f'❌ Unknown service: `{svc}`')
                return 'OK'
            code, out, err = run_cmd(f'supervisorctl status {svc}')
            send_message(chat_id, f'📊 *{SERVICES.get(svc, svc)}*\n```\n{out or "Not found"}\n```')
        
        elif cmd in ['/restart', '/stop', '/start']:
            if len(parts) < 2:
                send_message(chat_id, f'Usage: `{cmd} <service>`')
                return 'OK'
            svc = parts[1]
            if svc not in SERVICES:
                send_message(chat_id, f'❌ Unknown service: `{svc}`')
                return 'OK'
            action = cmd[1:]  # remove /
            send_message(chat_id, f'⏳ {action.capitalize()}ing `{svc}`...')
            code, out, err = run_cmd(f'supervisorctl {action} {svc}')
            status = '✅ Success' if code == 0 else '❌ Failed'
            send_message(chat_id, f'{status}: `{svc}` {action}\n```\n{out or err}\n```')
        
        elif cmd == '/logs':
            if len(parts) < 2:
                send_message(chat_id, 'Usage: `/logs <service> [lines]`')
                return 'OK'
            svc = parts[1]
            lines = int(parts[2]) if len(parts) > 2 else 50
            if svc not in SERVICES:
                send_message(chat_id, f'❌ Unknown service: `{svc}`')
                return 'OK'
            
            log_map = {
                'sshd': '/var/log/supervisor/sshd.log',
                'bore-tunnels': '/var/log/supervisor/bore.log',
                'bot-1': '/var/log/bots/bot1.log',
                'bot-2': '/var/log/bots/bot2.log',
                'bot-3': '/var/log/bots/bot3.log',
                'bot-4': '/var/log/bots/bot4.log',
                'flask-api': '/var/log/bots/flask.log',
                'monitoring': '/var/log/bots/monitor.log',
            }
            log_file = log_map.get(svc)
            if not log_file or not os.path.exists(log_file):
                send_message(chat_id, f'❌ Log file not found for `{svc}`')
                return 'OK'
            
            code, out, err = run_cmd(f'tail -n {lines} {log_file}')
            if out:
                send_message(chat_id, f'📜 *Logs: {svc} (last {lines})*\n```\n{out[-4000:]}\n```')
            else:
                send_message(chat_id, '📭 No logs')
        
        elif cmd == '/sysinfo':
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net = psutil.net_io_counters()
            
            send_message(chat_id,
                f'💻 *System Info*\n'
                f'CPU: `{cpu}%`\n'
                f'RAM: `{mem.percent}%` ({mem.used//1024//1024}MB/{mem.total//1024//1024}MB)\n'
                f'Disk: `{disk.percent}%` ({disk.used//1024//1024}MB/{disk.total//1024//1024}MB)\n'
                f'Net: ↑{net.bytes_sent//1024//1024}MB ↓{net.bytes_recv//1024//1024}MB\n'
                f'Processes: `{len(psutil.pids())}`')
        
        elif cmd == '/exec':
            if len(parts) < 2:
                send_message(chat_id, 'Usage: `/exec <command>`')
                return 'OK'
            command = ' '.join(parts[1:])
            send_message(chat_id, f'⏳ Executing: `{command}`')
            code, out, err = run_cmd(command, timeout=60)
            result = out if out else err
            status = '✅' if code == 0 else '❌'
            send_message(chat_id, f'{status} Exit code: `{code}`\n```\n{result[-3500:]}\n```')
        
        elif cmd == '/help':
            send_message(chat_id,
                '🖥️ *System Control Bot Help*\n\n'
                '`/services` - List all services\n'
                '`/status <svc>` - Service status\n'
                '`/restart <svc>` - Restart service\n'
                '`/stop <svc>` - Stop service\n'
                '`/start <svc>` - Start service\n'
                '`/logs <svc> [lines]` - View logs\n'
                '`/sysinfo` - System info\n'
                '`/exec <cmd>` - Execute command\n'
                '`/help` - This help')
        
        else:
            send_message(chat_id, f'❓ Unknown: `{cmd}`. Use `/help`')
    
    except Exception as e:
        send_message(chat_id, f'❌ Error: `{str(e)}`')
    
    return 'OK'

if __name__ == '__main__':
    webhook_url = os.getenv('WEBHOOK_URL_4', os.getenv('WEBHOOK_URL_1', ''))
    if webhook_url and BOT_TOKEN != 'YOUR_BOT_TOKEN':
        url = f'{webhook_url.rstrip("/")}/{BOT_TOKEN}'
        requests.post(f'{API_URL}/setWebhook', json={'url': url, 'drop_pending_updates': True}, timeout=10)
        print(f'Webhook set: {url}')
    
    app.run(host='0.0.0.0', port=5003, threaded=True)