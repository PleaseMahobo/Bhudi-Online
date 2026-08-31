"""Bhudi Windows tray companion.

Runs in the interactive user session and submits endpoint support tickets
through the authenticated agent-support API. The background RMM service remains
separate and does not expose UI.
"""
import json
import os
import platform
import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from urllib import request, error

APP_NAME = "Bhudi Support"
CONFIG_PATH = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "Bhudi", "tray.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def diagnostics():
    return {"hostname": socket.gethostname(), "platform": platform.platform(), "user": os.environ.get("USERNAME")}

def submit_ticket(payload):
    cfg = load_config()
    body = json.dumps({**payload, "description": payload["description"] + "\n\nDiagnostics: " + json.dumps(diagnostics())}).encode()
    url = cfg["api_base"].rstrip("/") + "/api/v1/agent-support/tickets?agent_id=" + cfg["agent_id"]
    req = request.Request(url, data=body, method="POST", headers={"Content-Type":"application/json","X-Bhudi-Agent-Token":cfg["agent_token"]})
    with request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())

def show_ticket_window():
    win = tk.Tk(); win.title("Log a Bhudi Support Ticket"); win.geometry("520x420")
    ttk.Label(win, text="Subject").pack(anchor="w", padx=16, pady=(16,2))
    title = ttk.Entry(win); title.pack(fill="x", padx=16)
    ttk.Label(win, text="Describe the problem").pack(anchor="w", padx=16, pady=(12,2))
    description = tk.Text(win, height=12); description.pack(fill="both", expand=True, padx=16)
    priority = ttk.Combobox(win, values=["low","medium","high","critical"], state="readonly"); priority.set("medium"); priority.pack(fill="x", padx=16, pady=12)
    def send():
        if not title.get().strip():
            messagebox.showerror(APP_NAME, "Please enter a subject."); return
        try:
            result = submit_ticket({"title":title.get().strip(),"description":description.get("1.0","end").strip(),"priority":priority.get(),"requester":os.environ.get("USERNAME")})
            messagebox.showinfo(APP_NAME, "Ticket created: " + str(result.get("number") or result.get("id")))
            win.destroy()
        except error.HTTPError as exc:
            messagebox.showerror(APP_NAME, "Ticket submission failed: HTTP " + str(exc.code))
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Ticket submission failed: " + str(exc))
    ttk.Button(win, text="Submit Ticket", command=lambda: threading.Thread(target=send, daemon=True).start()).pack(pady=12)
    win.mainloop()

if __name__ == "__main__":
    show_ticket_window()
