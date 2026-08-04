import websocket
import json
import subprocess

DEVICE_ID = "device-001"

WS_URL = f"ws://127.0.0.1:8000/api/live/agent/{DEVICE_ID}"


def on_message(ws, message):

    data = json.loads(message)

    if data["type"] == "command":

        command = data["command"]

        try:

            result = subprocess.check_output(
                command,
                shell=True,
                stderr=subprocess.STDOUT,
                text=True
            )

        except subprocess.CalledProcessError as e:
            result = str(e.output)

        ws.send(json.dumps({
            "output": result
        }))


def on_open(ws):
    print("Connected to RMM shell")


ws = websocket.WebSocketApp(
    WS_URL,
    on_message=on_message,
    on_open=on_open
)

ws.run_forever()