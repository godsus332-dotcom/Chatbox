from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit

from database import (
    init_db, get_user, add_user, delete_user,
    save_message, get_recent_messages,
    delete_old_messages, clear_messages,
    set_muted, set_banned, change_password,
    list_users
)

import os
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# ✅ FIX eventlet issue
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ================= INIT =================
init_db()

# create default admin
if not get_user("luxcifer"):
    add_user("luxcifer", "0456", "admin")

active_users = {}  # sid -> username


# ================= CONNECT =================
@socketio.event
def connect():
    print("CLIENT CONNECTED")


# ================= ROUTE =================
@app.route('/')
def index():
    return render_template("index.html")


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

    # 🔥 send last 24h messages
    messages = get_recent_messages()
    for msg in messages:
        emit("message", msg)

    send(f"[SYSTEM] {username} joined", broadcast=True)
    emit("user_list", list(active_users.values()), broadcast=True)


# ================= MESSAGE =================
@socketio.on("message")
def handle_message(msg):
    username = active_users.get(request.sid)
    if not username:
        return

    user = get_user(username)

    # ❌ muted user
    if user["muted"]:
        send("[SYSTEM] You are muted", to=request.sid)
        return

    # ================= COMMANDS =================
    if msg.startswith("/"):
        parts = msg.split()

        # ---------- ADMIN COMMANDS ----------
        if user["role"] == "admin":

            if parts[0] == "/adduser":
                add_user(parts[1], parts[2])
                send(f"[SYSTEM] User {parts[1]} added", to=request.sid)

            elif parts[0] == "/deluser":
                delete_user(parts[1])
                send(f"[SYSTEM] User {parts[1]} deleted", to=request.sid)

            elif parts[0] == "/mute":
                set_muted(parts[1], True)
                send(f"[SYSTEM] {parts[1]} muted", broadcast=True)

            elif parts[0] == "/unmute":
                set_muted(parts[1], False)
                send(f"[SYSTEM] {parts[1]} unmuted", broadcast=True)

            elif parts[0] == "/ban":
                set_banned(parts[1], True)
                send(f"[SYSTEM] {parts[1]} banned", broadcast=True)

            elif parts[0] == "/unban":
                set_banned(parts[1], False)
                send(f"[SYSTEM] {parts[1]} unbanned", broadcast=True)

            elif parts[0] == "/kick":
                target = parts[1]
                for sid, u in list(active_users.items()):
                    if u == target:
                        emit("force_disconnect", to=sid)
                        active_users.pop(sid, None)
                        send(f"[SYSTEM] {target} kicked", broadcast=True)

            elif parts[0] == "/clear":
                clear_messages()
                emit("clear_chat", broadcast=True)

            elif parts[0] == "/lsusers":
                users = list_users()
                send("[SYSTEM] Users: " + ", ".join(users), to=request.sid)

        # ---------- COMMON COMMANDS ----------
        if parts[0] == "/changepass":
            change_password(username, parts[1], parts[2])
            send("[SYSTEM] Password updated", to=request.sid)

        elif parts[0] == "/whoami":
            send(f"[SYSTEM] You are {username}", to=request.sid)

        elif parts[0] == "/help":
            send("""
[SYSTEM COMMANDS]

User:
 /changepass <old> <new>
 /whoami
 /help

Admin:
 /adduser <u> <p>
 /deluser <u>
 /mute <u> /unmute <u>
 /ban <u> /unban <u>
 /kick <u>
 /clear
 /lsusers
""", to=request.sid)

        return

    # ================= NORMAL MESSAGE =================
    formatted = f"[{username}] {msg}"
    save_message(formatted)

    # delete old messages (24h cleanup)
    delete_old_messages()

    send(formatted, broadcast=True)


# ================= DISCONNECT =================
@socketio.event
def disconnect():
    username = active_users.pop(request.sid, None)

    if username:
        send(f"[SYSTEM] {username} left", broadcast=True)
        emit("user_list", list(active_users.values()), broadcast=True)


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
