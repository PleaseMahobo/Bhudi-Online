from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Root SQLAlchemy declarative base for the entire Bhudi-Online backend.

    Every ORM model in the project MUST inherit from this class.
    """

    pass