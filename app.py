from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, send
import database

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, async_mode="threading")

database.init_db()

active_users = {}
authenticated = {}
banned_users = set()

@app.route("/")
def index():
    return render_template("index.html")

# ================= LOGIN =================
@socketio.on("login")
def login(data):
    username = data["username"]
    password = data["password"]

    user = database.get_user(username)

    if username in banned_users:
        emit("login_error", "You are banned")
        return

    if user and user[1] == password:
        authenticated[request.sid] = username
        active_users[request.sid] = username

        emit("login_success", {"username": username})

        # send last 24h chat
        for msg in database.get_recent_messages():
            emit("message", msg)

        socketio.emit("user_list", list(active_users.values()))
        send(f"[SYSTEM] {username} joined", broadcast=True)

    else:
        emit("login_error", "Invalid credentials")

# ================= MESSAGE =================
@socketio.on("message")
def handle_message(msg):
    if request.sid not in authenticated:
        return

    username = authenticated[request.sid]
    user = database.get_user(username)
    role = user[2]

    # COMMANDS
    if msg.startswith("/"):
        parts = msg.split()
        cmd = parts[0]

        if role != "admin":
            send("[SYSTEM] Admin only command", to=request.sid)
            return

        if cmd == "/adduser":
            database.add_user(parts[1], parts[2])
            send(f"[SYSTEM] User {parts[1]} added")

        elif cmd == "/deluser":
            database.delete_user(parts[1])
            send(f"[SYSTEM] User {parts[1]} deleted")

        elif cmd == "/kick":
            for sid, u in active_users.items():
                if u == parts[1]:
                    socketio.disconnect(sid)

        elif cmd == "/ban":
            banned_users.add(parts[1])
            send(f"[SYSTEM] {parts[1]} banned")

        elif cmd == "/unban":
            banned_users.discard(parts[1])
            send(f"[SYSTEM] {parts[1]} unbanned")

        elif cmd == "/lsusers":
            users = database.get_all_users()
            send("[SYSTEM] Users: " + ", ".join(users))

        return

    # NORMAL MESSAGE
    formatted = f"[{username}] {msg}"
    database.save_message(username, msg)

    for sid in authenticated:
        socketio.emit("message", formatted, to=sid)

# ================= DISCONNECT =================
@socketio.on("disconnect")
def disconnect():
    sid = request.sid
    username = authenticated.pop(sid, None)
    active_users.pop(sid, None)

    if username:
        send(f"[SYSTEM] {username} left", broadcast=True)
        socketio.emit("user_list", list(active_users.values()))

# ================= RUN =================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
