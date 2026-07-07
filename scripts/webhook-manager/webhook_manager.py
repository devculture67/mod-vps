#!/usr/bin/env python3
"""
Webhook Manager - Auto-manage webhooks for multiple Telegram bots
Handles: set, delete, info, list webhooks
"""

import os
import sys
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOTS = {}
BOT_PASSWORD = os.getenv('BOT_PASSWORD', 'rairukun2025')

def load_bots():
    """Load bot configs from env"""
    global BOTS
    i = 1
    while True:
        token = os.getenv(f'BOT_TOKEN_{i}')
        url = os.getenv(f'WEBHOOK_URL_{i}')
        if not token:
            break
        BOTS[f'bot{i}'] = {
            'token': token,
            'webhook_url': url,
            'api_url': f'https://api.telegram.org/bot{token}'
        }
        i += 1

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'webhook-manager', 'bots_loaded': len(BOTS)})

@app.route('/webhook/set', methods=['POST'])
def set_webhook():
    """Set webhook for a bot"""
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    bot_name = data.get('bot', 'bot1')
    url = data.get('url')
    secret_token = data.get('secret_token')
    allowed_updates = data.get('allowed_updates', ['message', 'callback_query', 'edited_message'])
    
    if bot_name not in BOTS:
        return jsonify({'error': f'Bot {bot_name} not configured'}), 404
    
    if not url:
        url = BOTS[bot_name].get('webhook_url')
    
    if not url:
        return jsonify({'error': 'No webhook URL provided'}), 400
    
    webhook_url = f'{url.rstrip("/")}/{BOTS[bot_name]["token"]}'
    
    payload = {
        'url': webhook_url,
        'allowed_updates': allowed_updates,
        'drop_pending_updates': data.get('drop_pending', True)
    }
    if secret_token:
        payload['secret_token'] = secret_token
    
    r = requests.post(f'{BOTS[bot_name]["api_url"]}/setWebhook', json=payload, timeout=10)
    return jsonify(r.json())

@app.route('/webhook/delete', methods=['POST'])
def delete_webhook():
    """Delete webhook for a bot"""
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    bot_name = data.get('bot', 'bot1')
    if bot_name not in BOTS:
        return jsonify({'error': f'Bot {bot_name} not configured'}), 404
    
    r = requests.post(f'{BOTS[bot_name]["api_url"]}/deleteWebhook', json={'drop_pending_updates': True}, timeout=10)
    return jsonify(r.json())

@app.route('/webhook/info', methods=['GET'])
def get_webhook_info():
    """Get webhook info for a bot"""
    bot_name = request.args.get('bot', 'bot1')
    if bot_name not in BOTS:
        return jsonify({'error': f'Bot {bot_name} not configured'}), 404
    
    r = requests.get(f'{BOTS[bot_name]["api_url"]}/getWebhookInfo', timeout=10)
    return jsonify(r.json())

@app.route('/webhook/list', methods=['GET'])
def list_webhooks():
    """List all bot webhook statuses"""
    results = {}
    for name, config in BOTS.items():
        try:
            r = requests.get(f'{config["api_url"]}/getWebhookInfo', timeout=5)
            results[name] = r.json()
        except Exception as e:
            results[name] = {'error': str(e)}
    return jsonify(results)

@app.route('/webhook/auto-set', methods=['POST'])
def auto_set_all():
    """Auto-set webhooks for all configured bots"""
    data = request.get_json() or {}
    if data.get('password') != BOT_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 403
    
    results = {}
    for name, config in BOTS.items():
        if config.get('webhook_url'):
            url = f'{config["webhook_url"].rstrip("/")}/{config["token"]}'
            r = requests.post(f'{config["api_url"]}/setWebhook', 
                json={'url': url, 'allowed_updates': ['message', 'callback_query'], 'drop_pending_updates': True},
                timeout=10)
            results[name] = r.json()
        else:
            results[name] = {'error': 'No webhook_url configured'}
    
    return jsonify(results)

if __name__ == '__main__':
    load_bots()
    print(f"Loaded {len(BOTS)} bot(s): {list(BOTS.keys())}")
    app.run(host='0.0.0.0', port=8888, threaded=True)