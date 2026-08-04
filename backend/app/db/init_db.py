from app.database.database import Base, engine
from app.models import device  # ensure model import

def init_db():
    Base.metadata.create_all(bind=engine)