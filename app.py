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

socketio = SocketIO(app, async_mode="threading")

init_db()

if not get_user("luxcifer"):
    add_user("luxcifer", "0456", "admin")

active_users = {}


@app.route('/')
def index():
    return render_template("index.html")


# ================= LOGIN =================
@socketio.on("login")
def login(data):
    print("LOGIN EVENT RECIVED:", data)

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

    history = get_recent_messages()
    fixed_history = []
    for msg in history:
        if msg.startswith("[") and "]" in msg:
            fixed_history.append(msg)
        else:
            fixed_history.append(f"[UNKNOWN] {msg}")

    emit("chat_history", fixed_history)

    # 🔥 FIXED (WAS send)
    emit("message", {"user": "SYSTEM", "msg": f"{username} joined"}, broadcast=True)

    emit("user_list", list(active_users.values()), broadcast=True)


# ================= MESSAGE =================
@socketio.on("message")
def handle_message(msg):
    username = active_users.get(request.sid)
    if not username:
        return

    user = get_user(username)

    if user["muted"]:
        emit("message", {"user": "SYSTEM", "msg": "You are muted"}, to=request.sid)
        return

    if msg.startswith("/"):
        parts = msg.split()
        cmd = parts[0]

        if cmd == "/help":
            emit("message", {
                "user": "SYSTEM",
                "msg": """COMMANDS:
/help
/whoami
/changepass <old> <new>"""
            }, to=request.sid)
            return

        if cmd == "/whoami":
            emit("message", {
                "user": "SYSTEM",
                "msg": f"{username} | role={user['role']} | muted={user['muted']} | banned={user['banned']}"
            }, to=request.sid)
            return

        if cmd == "/changepass":
            if len(parts) < 3:
                emit("message", {"user": "SYSTEM", "msg": "Usage: /changepass old new"}, to=request.sid)
                return

            if user["password"] != parts[1]:
                emit("message", {"user": "SYSTEM", "msg": "Wrong old password"}, to=request.sid)
                return

            change_password(username, parts[2])
            emit("message", {"user": "SYSTEM", "msg": "Password changed"}, to=request.sid)
            return

        if user["role"] != "admin":
            emit("message", {"user": "SYSTEM", "msg": "Admin only command"}, to=request.sid)
            return

        if cmd == "/adduser" and len(parts) >= 3:
            add_user(parts[1], parts[2])
            emit("message", {"user": "SYSTEM", "msg": f"User {parts[1]} added"}, to=request.sid)

        elif cmd == "/deluser" and len(parts) >= 2:
            delete_user(parts[1])
            emit("message", {"user": "SYSTEM", "msg": f"User {parts[1]} deleted"}, to=request.sid)

        elif cmd == "/mute" and len(parts) >= 2:
            set_muted(parts[1], 1)
            emit("message", {"user": "SYSTEM", "msg": f"{parts[1]} muted"}, broadcast=True)

        elif cmd == "/unmute" and len(parts) >= 2:
            set_muted(parts[1], 0)
            emit("message", {"user": "SYSTEM", "msg": f"{parts[1]} unmuted"}, broadcast=True)

        elif cmd == "/ban" and len(parts) >= 2:
            set_banned(parts[1], 1)
            emit("message", {"user": "SYSTEM", "msg": f"{parts[1]} banned"}, broadcast=True)

        elif cmd == "/unban" and len(parts) >= 2:
            set_banned(parts[1], 0)
            emit("message", {"user": "SYSTEM", "msg": f"{parts[1]} unbanned"}, broadcast=True)

        elif cmd == "/lsusers":
            users = list_users()
            emit("message", {"user": "SYSTEM", "msg": "Users: " + ", ".join(users)}, to=request.sid)

        return

    # 🔥 FIXED (WAS send)
    save_message(username, msg)
    emit("message", {"user": username, "msg": msg}, broadcast=True)


# ================= DISCONNECT =================
@socketio.on("disconnect")
def disconnect():
    username = active_users.pop(request.sid, None)

    if username:
        # 🔥 FIXED (WAS send)
        emit("message", {"user": "SYSTEM", "msg": f"{username} left"}, broadcast=True)
        emit("user_list", list(active_users.values()), broadcast=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
