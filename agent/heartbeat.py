import time
from collector import collect_system_data
from client import send_heartbeat

def run_agent():
    while True:
        data = collect_system_data()

        status, response = send_heartbeat(data)

        print(f"[AGENT] Sent heartbeat: {status} - {response}")

        time.sleep(30)  # heartbeat interval