import sqlite3
from datetime import datetime, timedelta

DB = "chat.db"


def connect():
    return sqlite3.connect(DB)


def init_db():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT DEFAULT 'user',
        banned INTEGER DEFAULT 0,
        muted INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        message TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()


# ================= USERS =================

def get_user(username):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "username": row[0],
        "password": row[1],
        "role": row[2],
        "banned": row[3],
        "muted": row[4]
    }


def add_user(username, password, role="user"):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, 0, 0)",
              (username, password, role))
    conn.commit()
    conn.close()


def delete_user(username):
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()


def list_users():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users


def set_muted(username, value):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE users SET muted=? WHERE username=?", (value, username))
    conn.commit()
    conn.close()


def set_banned(username, value):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE users SET banned=? WHERE username=?", (value, username))
    conn.commit()
    conn.close()


def change_password(username, new_pass):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE username=?", (new_pass, username))
    conn.commit()
    conn.close()


# ================= MESSAGES =================

def save_message(username, message):
    conn = connect()
    c = conn.cursor()

    c.execute(
        "INSERT INTO messages (username, message, timestamp) VALUES (?, ?, ?)",
        (username, message, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()


def get_recent_messages():
    conn = connect()
    c = conn.cursor()

    cutoff = datetime.now() - timedelta(hours=24)

    c.execute(
        "SELECT username, message FROM messages WHERE timestamp >= ?",
        (cutoff.isoformat(),)
    )

    rows = c.fetchall()
    conn.close()

    return [f"[{u}] {m}" for u, m in rows]


def delete_old_messages():
    conn = connect()
    c = conn.cursor()

    cutoff = datetime.now() - timedelta(hours=24)

    c.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff.isoformat(),))
    conn.commit()
    conn.close()


def clear_messages():
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()
