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
muted_users = set()
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
def is_admin(username):
    return users.get(username, {}).get("role") == "admin"

def clean_messages():
    now = time.time()
    return [m for m in messages if now - m[1] < 86400]

def broadcast_users():
    emit("user_list", list(active_users.values()), broadcast=True)

# ======================
# LOGIN
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
        emit("login_success", {"username": username, "role": users[username]["role"]})

        # send previous messages
        for msg, _ in clean_messages():
            emit("message", msg)

        broadcast_users()
    else:
        emit("login_error", "Invalid credentials")

# ======================
# DISCONNECT
# ======================
@socketio.on('disconnect')
def on_disconnect():
    if request.sid in active_users:
        active_users.pop(request.sid)
        broadcast_users()

# ======================
# TYPING
# ======================
@socketio.on('typing')
def typing():
    username = active_users.get(request.sid)
    emit("typing", f"{username} is typing...", broadcast=True)

# ======================
# MESSAGE HANDLER
# ======================
@socketio.on('message')
def handle_message(msg):
    username = active_users.get(request.sid, "Unknown")

    # ======================
    # COMMANDS
    # ======================
    if msg.startswith("/"):
        parts = msg.split()
        cmd = parts[0]

        def admin_only():
            if not is_admin(username):
                emit("message", "[SYSTEM] Admin only command")
                return False
            return True

        # /kick
        if cmd == "/kick" and admin_only():
            target = parts[1]
            for sid, user in list(active_users.items()):
                if user == target:
                    emit("message", f"[SYSTEM] {target} kicked", broadcast=True)
                    disconnect(sid)
                    return

        # /ban
        if cmd == "/ban" and admin_only():
            target = parts[1]
            banned_users.add(target)
            emit("message", f"[SYSTEM] {target} banned", broadcast=True)

        # /unban
        if cmd == "/unban" and admin_only():
            target = parts[1]
            banned_users.discard(target)
            emit("message", f"[SYSTEM] {target} unbanned", broadcast=True)

        # /adduser
        if cmd == "/adduser" and admin_only():
            target = parts[1]
            password = parts[2]
            users[target] = {"password": password, "role": "user"}
            emit("message", f"[SYSTEM] user {target} added", broadcast=True)

        # /deleteuser
        if cmd == "/deleteuser" and admin_only():
            target = parts[1]
            users.pop(target, None)
            emit("message", f"[SYSTEM] user {target} deleted", broadcast=True)

        # /changepass
        if cmd == "/changepass":
            if len(parts) < 3:
                return

            target = parts[1]
            newpass = parts[2]

            if target == username:
                users[username]["password"] = newpass
                emit("message", "[SYSTEM] password changed")
                return

            if admin_only():
                if target in users:
                    users[target]["password"] = newpass
                    emit("message", f"[SYSTEM] password changed for {target}", broadcast=True)

        # /mute
        if cmd == "/mute" and admin_only():
            target = parts[1]
            muted_users.add(target)
            emit("message", f"[SYSTEM] {target} muted", broadcast=True)

        # /unmute
        if cmd == "/unmute" and admin_only():
            target = parts[1]
            muted_users.discard(target)
            emit("message", f"[SYSTEM] {target} unmuted", broadcast=True)

        # /clear
        if cmd == "/clear" and admin_only():
            messages.clear()
            emit("message", "[SYSTEM] chat cleared", broadcast=True)

        # /whois
        if cmd == "/whois" and admin_only():
            target = parts[1]
            if target in users:
                role = users[target]["role"]
                emit("message", f"[SYSTEM] {target} role: {role}")

        return

    # ======================
    # BLOCK MUTED USERS
    # ======================
    if username in muted_users:
        emit("message", "[SYSTEM] You are muted")
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
