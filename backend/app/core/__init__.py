from app.core.database import Base, engine
from app.models import device  # ensures model is loaded


def init_db():
    Base.metadata.create_all(bind=engine)