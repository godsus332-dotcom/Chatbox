import sqlite3
import time

DB_NAME = "chat.db"

def connect():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        message TEXT,
        timestamp REAL
    )
    """)

    # ensure admin exists
    c.execute("SELECT * FROM users WHERE username=?", ("luxcifer",))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("luxcifer", "0456", "admin"))

    conn.commit()
    conn.close()


def add_user(username, password):
    conn = connect()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (username, password, "user"))
        conn.commit()
    except:
        pass
    conn.close()


def delete_user(username):
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()


def get_user(username):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user


def get_all_users():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    users = [u[0] for u in c.fetchall()]
    conn.close()
    return users


def save_message(username, message):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, message, timestamp) VALUES (?, ?, ?)",
              (username, message, time.time()))
    conn.commit()
    conn.close()


def get_recent_messages():
    conn = connect()
    c = conn.cursor()
    now = time.time()
    cutoff = now - 86400  # last 24 hours

    c.execute("SELECT username, message FROM messages WHERE timestamp >= ?", (cutoff,))
    rows = c.fetchall()
    conn.close()

    return [f"[{u}] {m}" for u, m in rows]


def clear_old_messages():
    conn = connect()
    c = conn.cursor()

    # midnight reset logic
    now = time.localtime()
    if now.tm_hour == 0 and now.tm_min == 0:
        c.execute("DELETE FROM messages")
        conn.commit()

    conn.close()
