import sys
import os

sys.path.append(os.path.dirname(__file__))

from app.database import engine, Base
from app.models.device import Device

print("Creating tables...")

Base.metadata.create_all(bind=engine)

print("Done.")