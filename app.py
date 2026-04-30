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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# FIX eventlet issue
socketio = SocketIO(app, async_mode="threading")

init_db()

# default admin
if not get_user("luxcifer"):
    add_user("luxcifer", "0456", "admin")

active_users = {}  # sid -> username


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

    delete_old_messages()

    emit("login_success", {"username": username})

    # send last 24h chat
    emit("chat_history", get_recent_messages())

    send(f"[SYSTEM] {username} joined", broadcast=True)
    emit("user_list", list(active_users.values()), broadcast=True)


# ================= MESSAGE =================
@socketio.on("message")
def handle_message(msg):
    username = active_users.get(request.sid)
    if not username:
        return

    user = get_user(username)

    # muted check
    if user["muted"]:
        send("[SYSTEM] You are muted", to=request.sid)
        return

    # ================= COMMANDS =================
    if msg.startswith("/"):
        parts = msg.split()
        cmd = parts[0]

        # ===== USER COMMANDS =====
        if cmd == "/help":
            send("""[SYSTEM COMMANDS]
/help
/whoami
/changepass <old> <new>

[ADMIN ONLY]
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
            send(f"[SYSTEM] {username} | role={user['role']} | muted={user['muted']} | banned={user['banned']}", to=request.sid)
            return

        if cmd == "/changepass":
            if len(parts) < 3:
                send("[SYSTEM] Usage: /changepass old new", to=request.sid)
                return

            if user["password"] != parts[1]:
                send("[SYSTEM] Wrong old password", to=request.sid)
                return

            change_password(username, parts[2])
            send("[SYSTEM] Password changed", to=request.sid)
            return

        # ===== ADMIN CHECK =====
        if user["role"] != "admin":
            send("[SYSTEM] Admin only command", to=request.sid)
            return

        # ===== ADMIN COMMANDS =====
        if cmd == "/adduser" and len(parts) >= 3:
            add_user(parts[1], parts[2])
            send(f"[SYSTEM] User {parts[1]} added", to=request.sid)

        elif cmd == "/deluser" and len(parts) >= 2:
            delete_user(parts[1])
            send(f"[SYSTEM] User {parts[1]} deleted", to=request.sid)

        elif cmd == "/mute" and len(parts) >= 2:
            set_muted(parts[1], 1)
            send(f"[SYSTEM] {parts[1]} muted", broadcast=True)

        elif cmd == "/unmute" and len(parts) >= 2:
            set_muted(parts[1], 0)
            send(f"[SYSTEM] {parts[1]} unmuted", broadcast=True)

        elif cmd == "/ban" and len(parts) >= 2:
            set_banned(parts[1], 1)
            send(f"[SYSTEM] {parts[1]} banned", broadcast=True)

        elif cmd == "/unban" and len(parts) >= 2:
            set_banned(parts[1], 0)
            send(f"[SYSTEM] {parts[1]} unbanned", broadcast=True)

        elif cmd == "/kick" and len(parts) >= 2:
            target = parts[1]
            for sid, usern in list(active_users.items()):
                if usern == target:
                    emit("force_disconnect", to=sid)
                    active_users.pop(sid)
                    send(f"[SYSTEM] {target} kicked", broadcast=True)

        elif cmd == "/clear":
            clear_messages()
            send("[SYSTEM] Chat cleared", broadcast=True)

        elif cmd == "/lsusers":
            users = list_users()
            send("[SYSTEM] Users: " + ", ".join(users), to=request.sid)

        return

    # ===== NORMAL MESSAGE =====
    save_message(username, msg)
    send(f"[{username}] {msg}", broadcast=True)


# ================= DISCONNECT =================
@socketio.on("disconnect")
def disconnect():
    username = active_users.pop(request.sid, None)

    if username:
        send(f"[SYSTEM] {username} left", broadcast=True)
        emit("user_list", list(active_users.values()), broadcast=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
