from app.core.database import Base, engine
from app.models import device  # noqa

def init_db():
    Base.metadata.create_all(bind=engine)