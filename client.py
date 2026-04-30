import socketio
import datetime
import os
import sys
from rich import print
from rich.console import Console

console = Console()

SERVER_URL = "https://chatbox-akz3.onrender.com"

# 🔥 Stable client (no eventlet)
sio = socketio.Client(
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=2,
    async_mode="threading"
)

username = input("Username: ")
password = input("Password: ")

logged_in = False


# =========================
# CONNECT
# =========================
@sio.event
def connect():
    console.print("[bold green][+] Connected to server[/bold green]")
    sio.emit("login", {"username": username, "password": password})


@sio.event
def disconnect():
    console.print("[red][-] Disconnected[/red]")


# =========================
# LOGIN
# =========================
@sio.on("login_success")
def login_ok(data):
    global logged_in
    logged_in = True
    console.print(f"[bold green][+] Logged in as {data['username']}[/bold green]")


@sio.on("login_error")
def login_fail(msg):
    console.print(f"[bold red][!] Login failed:[/bold red] {msg}")
    sio.disconnect()
    sys.exit()


# =========================
# MESSAGE DISPLAY
# =========================
@sio.on("message")
def on_message(msg):
    if not logged_in:
        return

    now = datetime.datetime.now().strftime("%H:%M:%S")

    # Color system messages differently
    if "[SYSTEM]" in msg:
        console.print(f"[yellow][{now}][/yellow] {msg}")
    else:
        console.print(f"[green][{now}][/green] {msg}")

    # 🔔 Beep
    os.system("printf '\\a'")


# =========================
# ONLINE USERS
# =========================
@sio.on("user_list")
def users(data):
    if not logged_in:
        return

    console.print("\n[cyan]==== ONLINE USERS ==== [/cyan]")
    for u in data:
        console.print(f"[bold green]>>[/bold green] {u}")
    console.print()


# =========================
# CONNECT
# =========================
try:
    sio.connect(SERVER_URL, transports=["websocket"])
except Exception as e:
    console.print("[red]Connection error:[/red]", e)
    sys.exit()


# =========================
# INPUT LOOP
# =========================
while True:
    try:
        msg = input("[bold green]> [/bold green]")

        # 🚫 block input until login success
        if not logged_in:
            console.print("[yellow]Waiting for login...[/yellow]")
            continue

        if msg.strip() == "":
            continue

        sio.send(msg)

    except KeyboardInterrupt:
        console.print("\n[red]Exiting...[/red]")
        break


sio.disconnect()
