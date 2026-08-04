import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models.device import Device  # IMPORTANT

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Done.")