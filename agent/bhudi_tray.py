"""Bhudi persistent Windows system-tray companion."""
import ctypes, json, os, platform, socket, threading, tkinter as tk
from tkinter import messagebox, ttk
from urllib import request, error

APP_NAME="Bhudi Support"
CONFIG_PATH=os.path.join(os.environ.get("PROGRAMDATA",r"C:\\ProgramData"),"Bhudi","tray.json")

def load_config():
    with open(CONFIG_PATH,encoding="utf-8") as f: return json.load(f)

def diagnostics():
    return {"hostname":socket.gethostname(),"platform":platform.platform(),"user":os.environ.get("USERNAME")}

def submit_ticket(payload):
    cfg=load_config()
    body=json.dumps({**payload,"diagnostics":diagnostics()}).encode()
    url=cfg["api_base"].rstrip("/")+"/api/v1/agent-support/tickets?agent_id="+cfg["agent_id"]
    req=request.Request(url,data=body,method="POST",headers={"Content-Type":"application/json","X-Bhudi-Agent-Token":cfg["agent_token"]})
    with request.urlopen(req,timeout=20) as resp: return json.loads(resp.read().decode())

def ticket_window():
    win=tk.Toplevel(); win.title("Log a Bhudi Support Ticket"); win.geometry("520x430")
    ttk.Label(win,text="Subject").pack(anchor="w",padx=16,pady=(16,2))
    title=ttk.Entry(win); title.pack(fill="x",padx=16)
    ttk.Label(win,text="Describe the problem").pack(anchor="w",padx=16,pady=(12,2))
    desc=tk.Text(win,height=12); desc.pack(fill="both",expand=True,padx=16)
    priority=ttk.Combobox(win,values=["low","medium","high","critical"],state="readonly"); priority.set("medium"); priority.pack(fill="x",padx=16,pady=12)
    def send():
        if not title.get().strip(): messagebox.showerror(APP_NAME,"Please enter a subject."); return
        try:
            result=submit_ticket({"title":title.get().strip(),"description":desc.get("1.0","end").strip(),"priority":priority.get(),"requester":os.environ.get("USERNAME")})
            messagebox.showinfo(APP_NAME,"Ticket created: "+str(result.get("number") or result.get("id"))); win.destroy()
        except error.HTTPError as e: messagebox.showerror(APP_NAME,f"Ticket submission failed: HTTP {e.code}")
        except Exception as e: messagebox.showerror(APP_NAME,f"Ticket submission failed: {e}")
    ttk.Button(win,text="Submit Ticket",command=lambda:threading.Thread(target=send,daemon=True).start()).pack(pady=12)

def status():
    try:
        cfg=load_config()
        messagebox.showinfo(APP_NAME,f"Bhudi Agent: Connected\nDevice: {cfg.get('agent_id','Unknown')}")
    except Exception:
        messagebox.showwarning(APP_NAME,"Bhudi tray configuration is not available.")

def run_tray():
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        messagebox.showerror(APP_NAME,"Tray dependencies missing. Install pystray and Pillow."); return
    image=Image.new("RGB",(64,64),(30,60,110)); draw=ImageDraw.Draw(image); draw.rectangle((14,12,50,52),outline="white",width=4)
    root=tk.Tk(); root.withdraw()
    menu=pystray.Menu(
        pystray.MenuItem("Log a Ticket",lambda icon,item: root.after(0,ticket_window)),
        pystray.MenuItem("Agent Status",lambda icon,item: root.after(0,status)),
        pystray.MenuItem("Exit Bhudi Tray",lambda icon,item: (icon.stop(),root.destroy()))
    )
    icon=pystray.Icon("BhudiTray",image,APP_NAME,menu)
    threading.Thread(target=icon.run,daemon=True).start()
    root.mainloop()

if __name__=="__main__":
    run_tray()
