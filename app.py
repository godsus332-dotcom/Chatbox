from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit, disconnect
import time
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# =========================
# STORAGE
# =========================
users = {
    "luxcifer": {"password": "0456", "role": "admin"}
}

banned_users = set()
active_users = {}  # sid -> username
messages = []  # {user, msg, time}

MESSAGE_LIFETIME = 86400  # 24 hours

# =========================
# CLEAN OLD MESSAGES
# =========================
def clean_messages():
    now = time.time()
    global messages
    messages = [m for m in messages if now - m["time"] < MESSAGE_LIFETIME]

# =========================
# ROUTE
# =========================
@app.route('/')
def index():
    return render_template('index.html')

# =========================
# LOGIN
# =========================
@socketio.on('login')
def handle_login(data):
    username = data.get("username")
    password = data.get("password")

    if username in banned_users:
        emit("login_error", "You are banned")
        return

    if username in users and users[username]["password"] == password:
        active_users[request.sid] = username
        emit("login_success", {"username": username})
        emit("user_list", list(active_users.values()), broadcast=True)
        send(f"[SYSTEM] {username} joined", broadcast=True)
    else:
        emit("login_error", "Invalid credentials")

# =========================
# DISCONNECT
# =========================
@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_users:
        user = active_users.pop(request.sid)
        send(f"[SYSTEM] {user} left", broadcast=True)
        emit("user_list", list(active_users.values()), broadcast=True)

# =========================
# MESSAGE HANDLER
# =========================
@socketio.on('message')
def handle_message(msg):
    if request.sid not in active_users:
        return

    user = active_users[request.sid]

    # COMMANDS
    if msg.startswith('/'):
        handle_command(user, msg)
        return

    # NORMAL MESSAGE
    clean_messages()
    messages.append({
        "user": user,
        "msg": msg,
        "time": time.time()
    })

    send(f"[{user}] {msg}", broadcast=True)

# =========================
# COMMAND SYSTEM
# =========================
def handle_command(user, msg):
    parts = msg.split()
    cmd = parts[0]

    role = users[user]["role"]

    # ---------------------
    # ADMIN COMMANDS
    # ---------------------
    if role == "admin":

        if cmd == "/adduser" and len(parts) == 3:
            u, p = parts[1], parts[2]
            if u in users:
                send("[SYSTEM] User exists")
            else:
                users[u] = {"password": p, "role": "user"}
                send(f"[SYSTEM] User {u} added")

        elif cmd == "/deluser" and len(parts) == 2:
            u = parts[1]
            if u in users:
                del users[u]
                send(f"[SYSTEM] User {u} deleted")

        elif cmd == "/kick" and len(parts) == 2:
            target = parts[1]
            for sid, uname in list(active_users.items()):
                if uname == target:
                    disconnect(sid)
                    send(f"[SYSTEM] {target} kicked", broadcast=True)

        elif cmd == "/ban" and len(parts) == 2:
            target = parts[1]
            banned_users.add(target)
            send(f"[SYSTEM] {target} banned")

        elif cmd == "/unban" and len(parts) == 2:
            target = parts[1]
            banned_users.discard(target)
            send(f"[SYSTEM] {target} unbanned")

        elif cmd == "/clear":
            messages.clear()
            send("[SYSTEM] Chat cleared", broadcast=True)

    # ---------------------
    # USER COMMANDS
    # ---------------------
    if cmd == "/passwd" and len(parts) == 2:
        newpass = parts[1]
        users[user]["password"] = newpass
        send("[SYSTEM] Password changed")

    elif cmd == "/users":
        send("[SYSTEM] Online: " + ", ".join(active_users.values()))

    else:
        if cmd.startswith("/") and cmd not in [
            "/adduser","/deluser","/kick","/ban","/unban","/clear","/passwd","/users"
        ]:
            send("[SYSTEM] Unknown command")

# =========================
# RUN
# =========================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)
