from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit, disconnect
import os, time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# ======================
# DATA STORAGE
# ======================
users = {
    "luxcifer": {"password": "0456", "role": "admin"}
}

active_users = {}   # sid -> username
banned_users = set()
messages = []       # (msg, timestamp)

# ======================
# ROUTES
# ======================
@app.route('/')
def index():
    return render_template('index.html')

# ======================
# HELPERS
# ======================
def clean_messages():
    now = time.time()
    return [m for m in messages if now - m[1] < 86400]

def broadcast_users():
    emit("user_list", list(active_users.values()), broadcast=True)

def is_admin(username):
    return users.get(username, {}).get("role") == "admin"

# ======================
# SOCKET EVENTS
# ======================
@socketio.on('login')
def login(data):
    username = data['username']
    password = data['password']

    if username in banned_users:
        emit("login_error", "You are banned")
        return

    if username in users and users[username]['password'] == password:
        active_users[request.sid] = username
        emit("login_success", {"username": username})

        # send old messages
        for msg, _ in clean_messages():
            emit("message", msg)

        broadcast_users()

    else:
        emit("login_error", "Invalid credentials")

@socketio.on('disconnect')
def on_disconnect():
    if request.sid in active_users:
        active_users.pop(request.sid)
        broadcast_users()

@socketio.on('typing')
def typing():
    username = active_users.get(request.sid)
    emit("typing", f"{username} is typing...", broadcast=True)

@socketio.on('message')
def handle_message(msg):
    username = active_users.get(request.sid, "Unknown")

    # ======================
    # COMMANDS
    # ======================
    if msg.startswith("/"):
        parts = msg.split()

        if parts[0] == "/kick" and is_admin(username):
            target = parts[1]
            for sid, user in active_users.items():
                if user == target:
                    emit("message", f"[SYSTEM] {target} kicked", broadcast=True)
                    disconnect(sid)
                    return

        if parts[0] == "/ban" and is_admin(username):
            target = parts[1]
            banned_users.add(target)
            emit("message", f"[SYSTEM] {target} banned", broadcast=True)

        if parts[0] == "/unban" and is_admin(username):
            target = parts[1]
            banned_users.discard(target)
            emit("message", f"[SYSTEM] {target} unbanned", broadcast=True)

        return

    # ======================
    # NORMAL MESSAGE
    # ======================
    formatted = f"[{username}] {msg}"
    messages.append((formatted, time.time()))
    send(formatted, broadcast=True)

# ======================
# RUN
# ======================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)
