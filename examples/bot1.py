#!/usr/bin/env python3
"""
Example Bot 1 - Telegram Webhook
Replace BOT_TOKEN_1 with your actual token
"""
import os
import sys
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
BOT_TOKEN = os.getenv('BOT_TOKEN_1', 'YOUR_BOT_TOKEN_HERE')
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'bot': 'bot1'})

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data:
        return 'OK'
    
    if 'message' in data:
        msg = data['message']
        chat_id = msg['chat']['id']
        text = msg.get('text', '')
        
        if text == '/start':
            send_message(chat_id, '🤖 rairu-kun Bot 1 ready!')
        elif text == '/status':
            send_message(chat_id, '✅ Bot 1 running on rairu-kun')
        elif text == '/info':
            send_message(chat_id, f'Chat ID: {chat_id}\nContainer: rairu-kun-mod')
    
    return 'OK'

def send_message(chat_id, text):
    requests.post(f'{API_URL}/sendMessage', json={'chat_id': chat_id, 'text': text})

if __name__ == '__main__':
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print('ERROR: Set BOT_TOKEN_1 env var')
        sys.exit(1)
    
    # Set webhook
    webhook_url = os.getenv('WEBHOOK_URL_1', 'https://your-domain.ngrok-free.app')
    requests.post(f'{API_URL}/setWebhook', json={'url': f'{webhook_url}/{BOT_TOKEN}'})
    
    app.run(host='0.0.0.0', port=5000)