from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic SQLAlchemy repository.

    Provides common CRUD operations for all entities.
    Business logic belongs in the service layer, not here.
    """

    def __init__(
        self,
        session: Session,
        model: type[ModelT],
    ) -> None:
        self.session = session
        self.model = model

    # ---------------------------------------------------------
    # Read
    # ---------------------------------------------------------

    def get(self, entity_id):
        return self.session.get(self.model, entity_id)

    def list(self) -> list[ModelT]:
        return list(
            self.session.scalars(
                select(self.model)
            ).all()
        )

    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    def add(
        self,
        entity: ModelT,
    ) -> ModelT:
        self.session.add(entity)
        self.session.flush()
        self.session.refresh(entity)
        return entity

    # ---------------------------------------------------------
    # Update
    # ---------------------------------------------------------

    def save(
        self,
        entity: ModelT,
    ) -> ModelT:
        entity = self.session.merge(entity)
        self.session.flush()
        return entity

    # ---------------------------------------------------------
    # Delete
    # ---------------------------------------------------------

    def delete(
        self,
        entity: ModelT,
    ) -> None:
        self.session.delete(entity)
        self.session.flush()