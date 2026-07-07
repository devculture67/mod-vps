#!/usr/bin/env python3
"""
File Manager Bot - CRUD file operations via Telegram & HTTP API
Features: read, write, list, delete, upload, download
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import requests

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN_3', os.getenv('BOT_TOKEN_1', 'YOUR_BOT_TOKEN'))
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
BOT_PASSWORD = os.getenv('BOT_PASSWORD', 'rairukun2025')
BASE_PATH = Path(os.getenv('FILE_BASE_PATH', '/data')).resolve()
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB

# Ensure base path exists
BASE_PATH.mkdir(parents=True, exist_ok=True)

def safe_path(user_path: str) -> Path:
    """Resolve path and ensure it's within BASE_PATH"""
    target = (BASE_PATH / user_path).resolve()
    try:
        target.relative_to(BASE_PATH)
    except ValueError:
        raise ValueError("Path traversal attempt blocked")
    return target

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'file-manager', 'base_path': str(BASE_PATH)})

# ============================================================
# HTTP API ENDPOINTS
# ============================================================

@app.route('/api/file/read', methods=['POST'])
def api_read():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    path = data.get('path', '')
    try:
        target = safe_path(path)
        if not target.exists() or not target.is_file():
            return jsonify({'error': 'File not found'}), 404
        
        if target.stat().st_size > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large'}), 413
        
        content = target.read_text(encoding='utf-8', errors='replace')
        return jsonify({
            'path': str(target.relative_to(BASE_PATH)),
            'size': target.stat().st_size,
            'content': content
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/write', methods=['POST'])
def api_write():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    path = data.get('path', '')
    content = data.get('content', '')
    mode = data.get('mode', 'w')  # 'w' or 'a'
    
    try:
        target = safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return jsonify({
            'ok': True,
            'path': str(target.relative_to(BASE_PATH)),
            'size': len(content.encode('utf-8'))
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/list', methods=['POST'])
def api_list():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    path = data.get('path', '')
    try:
        target = safe_path(path)
        if not target.exists():
            return jsonify({'error': 'Path not found'}), 404
        
        if target.is_file():
            return jsonify({
                'path': str(target.relative_to(BASE_PATH)),
                'type': 'file',
                'size': target.stat().st_size,
                'modified': target.stat().st_mtime
            })
        
        items = []
        for item in target.iterdir():
            stat = item.stat()
            items.append({
                'name': item.name,
                'type': 'dir' if item.is_dir() else 'file',
                'size': stat.st_size if item.is_file() else 0,
                'modified': stat.st_mtime
            })
        
        return jsonify({
            'path': str(target.relative_to(BASE_PATH)),
            'items': sorted(items, key=lambda x: (x['type'] != 'dir', x['name']))
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/delete', methods=['POST'])
def api_delete():
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    path = data.get('path', '')
    recursive = data.get('recursive', False)
    
    try:
        target = safe_path(path)
        if not target.exists():
            return jsonify({'error': 'Not found'}), 404
        
        if target.is_dir():
            if recursive:
                import shutil
                shutil.rmtree(target)
            else:
                target.rmdir()  # only empty dirs
        else:
            target.unlink()
        
        return jsonify({'ok': True, 'path': str(target.relative_to(BASE_PATH))})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/download', methods=['GET'])
def api_download():
    path = request.args.get('path', '')
    password = request.args.get('password', '')
    if password != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    try:
        target = safe_path(path)
        if not target.exists() or not target.is_file():
            return jsonify({'error': 'File not found'}), 404
        return send_file(target, as_attachment=True)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/upload', methods=['POST'])
def api_upload():
    password = request.form.get('password', '')
    if password != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    path = request.form.get('path', '')
    file = request.files.get('file')
    
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400
    
    try:
        target = safe_path(path)
        if target.is_dir():
            target = target / file.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        file.save(target)
        return jsonify({
            'ok': True,
            'path': str(target.relative_to(BASE_PATH)),
            'size': target.stat().st_size
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
# TELEGRAM BOT HANDLERS
# ============================================================

def send_message(chat_id, text, parse_mode='Markdown'):
    requests.post(f'{API_URL}/sendMessage', json={
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }, timeout=10)

def send_document(chat_id, file_path, caption=''):
    with open(file_path, 'rb') as f:
        requests.post(f'{API_URL}/sendDocument', data={
            'chat_id': chat_id,
            'caption': caption
        }, files={'document': f}, timeout=30)

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or 'message' not in data:
        return 'OK'
    
    msg = data['message']
    chat_id = msg['chat']['id']
    text = msg.get('text', '')
    
    # Only allow authorized users (implement your auth)
    # if chat_id not in AUTHORIZED_USERS: return 'OK'
    
    parts = text.split(maxsplit=2)
    cmd = parts[0].lower() if parts else ''
    
    try:
        if cmd == '/start':
            send_message(chat_id, 
                '📁 *File Manager Bot*\n\n'
                'Commands:\n'
                '`/ls [path]` - List files\n'
                '`/cat <path>` - Read file\n'
                '`/write <path> <content>` - Write file\n'
                '`/mkdir <path>` - Create directory\n'
                '`/rm <path>` - Delete file/dir\n'
                '`/download <path>` - Download file\n'
                '`/tree [path]` - Tree view\n'
                '`/pwd` - Current directory')
        
        elif cmd == '/pwd':
            send_message(chat_id, f'📍 Base: `{BASE_PATH}`')
        
        elif cmd == '/ls':
            path = parts[1] if len(parts) > 1 else ''
            target = safe_path(path)
            if not target.exists() or not target.is_dir():
                send_message(chat_id, '❌ Not a directory')
                return 'OK'
            
            items = list(target.iterdir())[:50]
            lines = [f'📂 `{path or "."}`']
            for item in sorted(items, key=lambda x: (not x.is_dir(), x.name)):
                icon = '📁' if item.is_dir() else '📄'
                size = f" ({item.stat().st_size} bytes)" if item.is_file() else ''
                lines.append(f'{icon} `{item.name}`{size}')
            
            if len(items) == 50:
                lines.append('\n... (max 50 shown)')
            send_message(chat_id, '\n'.join(lines))
        
        elif cmd == '/cat':
            if len(parts) < 2:
                send_message(chat_id, 'Usage: `/cat <path>`')
                return 'OK'
            target = safe_path(parts[1])
            if not target.exists() or not target.is_file():
                send_message(chat_id, '❌ File not found')
                return 'OK'
            content = target.read_text(encoding='utf-8', errors='replace')[:4000]
            send_message(chat_id, f'📄 `{parts[1]}`\n```\n{content}\n```')
        
        elif cmd == '/write':
            if len(parts) < 3:
                send_message(chat_id, 'Usage: `/write <path> <content>`')
                return 'OK'
            target = safe_path(parts[1])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(parts[2], encoding='utf-8')
            send_message(chat_id, f'✅ Written: `{parts[1]}` ({len(parts[2])} chars)')
        
        elif cmd == '/mkdir':
            if len(parts) < 2:
                send_message(chat_id, 'Usage: `/mkdir <path>`')
                return 'OK'
            target = safe_path(parts[1])
            target.mkdir(parents=True, exist_ok=True)
            send_message(chat_id, f'📁 Created: `{parts[1]}`')
        
        elif cmd == '/rm':
            if len(parts) < 2:
                send_message(chat_id, 'Usage: `/rm <path>`')
                return 'OK'
            target = safe_path(parts[1])
            if not target.exists():
                send_message(chat_id, '❌ Not found')
                return 'OK'
            if target.is_dir():
                import shutil
                shutil.rmtree(target)
            else:
                target.unlink()
            send_message(chat_id, f'🗑️ Deleted: `{parts[1]}`')
        
        elif cmd == '/download':
            if len(parts) < 2:
                send_message(chat_id, 'Usage: `/download <path>`')
                return 'OK'
            target = safe_path(parts[1])
            if not target.exists() or not target.is_file():
                send_message(chat_id, '❌ File not found')
                return 'OK'
            if target.stat().st_size > MAX_FILE_SIZE:
                send_message(chat_id, '❌ File too large (>50MB)')
                return 'OK'
            send_document(chat_id, target, f'📎 `{parts[1]}`')
        
        elif cmd == '/tree':
            path = parts[1] if len(parts) > 1 else ''
            target = safe_path(path)
            lines = [f'🌳 `{path or "."}`']
            
            def add_tree(p, prefix='', max_depth=3, depth=0):
                if depth >= max_depth:
                    return
                try:
                    items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))[:20]
                    for i, item in enumerate(items):
                        is_last = i == len(items) - 1
                        icon = '📁' if item.is_dir() else '📄'
                        lines.append(f'{prefix}{"└── " if is_last else "├── "}{icon} `{item.name}`')
                        if item.is_dir() and depth < max_depth - 1:
                            add_tree(item, prefix + ('    ' if is_last else '│   '), max_depth, depth + 1)
                except PermissionError:
                    lines.append(f'{prefix}└── ❌ Permission denied')
            
            add_tree(target)
            send_message(chat_id, '\n'.join(lines))
        
        else:
            send_message(chat_id, f'❓ Unknown: `{cmd}`. Use `/start` for help.')
    
    except Exception as e:
        send_message(chat_id, f'❌ Error: `{str(e)}`')
    
    return 'OK'

if __name__ == '__main__':
    # Set webhook
    webhook_url = os.getenv('WEBHOOK_URL_3', os.getenv('WEBHOOK_URL_1', ''))
    if webhook_url and BOT_TOKEN != 'YOUR_BOT_TOKEN':
        url = f'{webhook_url.rstrip("/")}/{BOT_TOKEN}'
        requests.post(f'{API_URL}/setWebhook', json={'url': url, 'drop_pending_updates': True}, timeout=10)
        print(f'Webhook set: {url}')
    
    app.run(host='0.0.0.0', port=5002, threaded=True)