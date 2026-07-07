#!/usr/bin/env python3
"""
Example Bot 2 - HTTP API / Webhook
"""
import os
import sys
from flask import Flask, request, jsonify

app = Flask(__name__)
BOT_TOKEN = os.getenv('BOT_TOKEN_2', 'YOUR_BOT_TOKEN_HERE')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'bot': 'bot2'})

@app.route('/api/<path:path>', methods=['GET', 'POST'])
def api(path):
    data = request.get_json() or {}
    return jsonify({
        'received': True,
        'path': path,
        'method': request.method,
        'data': data
    })

@app.route('/exec', methods=['POST'])
def exec_cmd():
    """Execute command (use carefully!)"""
    cmd = request.json.get('cmd', '')
    if not cmd:
        return jsonify({'error': 'No command'}), 400
    
    import subprocess
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)