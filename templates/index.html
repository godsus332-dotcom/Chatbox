from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit, disconnect
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# IMPORTANT: no async_mode='threading'
socketio = SocketIO(app)

# =========================
# In-memory storage
# =========================
users = {
    "luxcifer": {"password": "0456", "role": "admin"}
}

banned_users = set()
active_users = {}   # sid -> username

# =========================
# Routes
# =========================
@app.route('/')
def index():
    return render_template('index.html')

# =========================
# Login system
# =========================
@socketio.on('login')
def handle_login(data):
    username = data.get("username")
    password = data.get("password")

    if username in banned_users:
        emit("login_response", {"status": "banned"})
        return

    if username in users and users[username]["password"] == password:
        active_users[request.sid] = username
        emit("login_response", {
            "status": "ok",
            "role": users[username]["role"]
        })
    else:
        emit("login_response", {"status": "fail"})

# =========================
# Chat messaging
# =========================
@socketio.on('message')
def handle_message(msg):
    user = active_users.get(request.sid)

    if not user:
        return

    send(f"{user}: {msg}", broadcast=True)

# =========================
# Admin: Kick user
# =========================
@socketio.on('kick')
def kick_user(data):
    admin = active_users.get(request.sid)

    if users.get(admin, {}).get("role") != "admin":
        return

    target = data.get("user")

    for sid, uname in list(active_users.items()):
        if uname == target:
            disconnect(sid=sid)
            del active_users[sid]

# =========================
# Admin: Ban user
# =========================
@socketio.on('ban')
def ban_user(data):
    admin = active_users.get(request.sid)

    if users.get(admin, {}).get("role") != "admin":
        return

    target = data.get("user")
    banned_users.add(target)

# =========================
# Admin: Unban user
# =========================
@socketio.on('unban')
def unban_user(data):
    admin = active_users.get(request.sid)

    if users.get(admin, {}).get("role") != "admin":
        return

    banned_users.discard(data.get("user"))

# =========================
# Admin: Add user
# =========================
@socketio.on('add_user')
def add_user(data):
    admin = active_users.get(request.sid)

    if users.get(admin, {}).get("role") != "admin":
        return

    username = data.get("username")
    password = data.get("password")

    if username not in users:
        users[username] = {
            "password": password,
            "role": "user"
        }

# =========================
# Admin: Delete user
# =========================
@socketio.on('delete_user')
def delete_user(data):
    admin = active_users.get(request.sid)

    if users.get(admin, {}).get("role") != "admin":
        return

    users.pop(data.get("username"), None)

# =========================
# Disconnect handler
# =========================
@socketio.on('disconnect')
def handle_disconnect():
    active_users.pop(request.sid, None)

# =========================
# Run (local only)
# =========================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)
