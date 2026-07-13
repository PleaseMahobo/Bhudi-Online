from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # Queries
    # =====================================================

    def get_by_email(
        self,
        email: str,
    ):

        return (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )

    def get_by_id(
        self,
        user_id,
    ):

        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def exists_by_email(
        self,
        email: str,
    ) -> bool:

        return self.get_by_email(email) is not None

    # =====================================================
    # Persistence
    # =====================================================

    def create(
        self,
        user: User,
    ):

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def save(
        self,
        user: User,
    ):

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def delete(
        self,
        user: User,
    ):

        self.db.delete(user)
        self.db.commit()