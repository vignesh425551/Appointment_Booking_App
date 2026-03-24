import uuid
import os
from datetime import datetime

SESSIONS_DIR = 'sessions'
LOGS_DIR = 'logs'

if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

def create_session(user_id):
    session_id = str(uuid.uuid4())
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    session_data = {
        'session_id': session_id,
        'user_id': user_id,
        'start_time': start_time
    }
    session_file = os.path.join(SESSIONS_DIR, f'{session_id}.txt')
    with open(session_file, 'w', encoding='utf-8') as f:
        for k, v in session_data.items():
            f.write(f'{k}: {v}\n')
    # Create an empty log file for the conversation
    log_file = os.path.join(LOGS_DIR, f'{session_id}.txt')
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f'Session started: {start_time}\n')
    return session_id

def log_message(session_id, message):
    log_file = os.path.join(LOGS_DIR, f'{session_id}.txt')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f'[{timestamp}] {message}\n') 