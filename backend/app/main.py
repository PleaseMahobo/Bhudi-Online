from fastapi import FastAPI
from app.core.database import engine, Base
from app.models.device import Device
import threading
import time
from app.workers.offline_detector import run_offline_detection
from app.db.init_db import init_db

@app.on_event("startup")
def startup():
    init_db()
    
app = FastAPI(title="Bhudi RMM")

def offline_loop():
    while True:
        run_offline_detection()
        time.sleep(30)  # runs every 30 seconds


@app.on_event("startup")
def startup():

    from app.core.database import engine, Base
    from app.models import device  # ensures models loaded

    Base.metadata.create_all(bind=engine)

    # start offline worker thread
    thread = threading.Thread(target=offline_loop, daemon=True)
    thread.start()

    print("RMM started: heartbeat + offline engine running")