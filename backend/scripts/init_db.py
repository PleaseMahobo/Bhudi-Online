import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import engine, Base
from app.models import device, command, alert

print("Creating tables...")

Base.metadata.create_all(bind=engine)

print("Done.")