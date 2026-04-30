from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from database import (
    init_db, get_user, add_user, delete_user,
    set_muted, set_banned, change_password,
    list_users,
    save_message, get_recent_messages, delete_old_messages, clear_messages
)

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# ✅ Stable config (NO eventlet issues)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ================= INIT =================
init_db()

# default admin
if not get_user("luxcifer"):
    add_user("luxcifer", "0456", "admin")

active_users = {}  # sid → username


# ================= ROUTE =================
@app.route('/')
def index():
    return render_template("index.html")


# ================= CONNECT =================
@socketio.event
def connect():
    print("CLIENT CONNECTED:", request.sid)


# ================= LOGIN =================
@socketio.on("login")
def login(data):
    username = data.get("username")
    password = data.get("password")

    user = get_user(username)

    if not user:
        emit("login_error", "User does not exist")
        return

    if user["password"] != password:
        emit("login_error", "Wrong password")
        return

    if user["banned"]:
        emit("login_error", "You are banned")
        return

    active_users[request.sid] = username

    emit("login_success", {"username": username})

    # 🔥 send chat history
    delete_old_messages()
    history = get_recent_messages()
    emit("chat_history", history)

    socketio.emit("message", f"[SYSTEM] {username} joined", broadcast=True)
    socketio.emit("user_list", list(active_users.values()), broadcast=True)


# ================= MESSAGE =================
@socketio.on("message")
def handle_message(msg):
    username = active_users.get(request.sid)

    print("MESSAGE RECEIVED:", msg)

    if not username:
        return

    user = get_user(username)

    # 🔇 muted user
    if user["muted"]:
        emit("message", "[SYSTEM] You are muted", to=request.sid)
        return

    # ================= COMMANDS =================
    if msg.startswith("/"):
        parts = msg.split()
        cmd = parts[0]

        # ===== COMMON =====
        if cmd == "/help":
            emit("message", """[COMMANDS]
/help
/whoami
/changepass <old> <new>

[ADMIN]
/adduser u p
/deluser u
/mute u
/unmute u
/ban u
/unban u
/kick u
/clear
/lsusers
""", to=request.sid)
            return

        if cmd == "/whoami":
            emit("message", f"[SYSTEM] You are {username}", to=request.sid)
            return

        if cmd == "/changepass" and len(parts) == 3:
            if user["password"] != parts[1]:
                emit("message", "[SYSTEM] Wrong old password", to=request.sid)
                return
            change_password(username, parts[2])
            emit("message", "[SYSTEM] Password updated", to=request.sid)
            return

        # ===== ADMIN ONLY =====
        if user["role"] != "admin":
            emit("message", "[SYSTEM] Admin only command", to=request.sid)
            return

        if cmd == "/adduser" and len(parts) == 3:
            add_user(parts[1], parts[2])
            emit("message", f"[SYSTEM] User {parts[1]} added", to=request.sid)

        elif cmd == "/deluser" and len(parts) == 2:
            delete_user(parts[1])
            emit("message", f"[SYSTEM] User {parts[1]} deleted", to=request.sid)

        elif cmd == "/mute" and len(parts) == 2:
            set_muted(parts[1], True)
            socketio.emit("message", f"[SYSTEM] {parts[1]} muted", broadcast=True)

        elif cmd == "/unmute" and len(parts) == 2:
            set_muted(parts[1], False)
            socketio.emit("message", f"[SYSTEM] {parts[1]} unmuted", broadcast=True)

        elif cmd == "/ban" and len(parts) == 2:
            set_banned(parts[1], True)
            socketio.emit("message", f"[SYSTEM] {parts[1]} banned", broadcast=True)

        elif cmd == "/unban" and len(parts) == 2:
            set_banned(parts[1], False)
            socketio.emit("message", f"[SYSTEM] {parts[1]} unbanned", broadcast=True)

        elif cmd == "/kick" and len(parts) == 2:
            target = parts[1]
            for sid, u in list(active_users.items()):
                if u == target:
                    socketio.emit("force_disconnect", to=sid)
                    active_users.pop(sid, None)
                    socketio.emit("message", f"[SYSTEM] {target} kicked", broadcast=True)

        elif cmd == "/clear":
            clear_messages()
            socketio.emit("clear_chat", broadcast=True)

        elif cmd == "/lsusers":
            users = list_users()
            emit("message", "[SYSTEM] Users: " + ", ".join(users), to=request.sid)

        return

    # ================= NORMAL MESSAGE =================
    formatted = f"[{username}] {msg}"

    save_message(username, msg)
    delete_old_messages()

    socketio.emit("message", formatted, broadcast=True)


# ================= DISCONNECT =================
@socketio.event
def disconnect():
    username = active_users.pop(request.sid, None)

    if username:
        socketio.emit("message", f"[SYSTEM] {username} left", broadcast=True)
        socketio.emit("user_list", list(active_users.values()), broadcast=True)


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
