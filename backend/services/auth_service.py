from app.core.security import create_jwt, verify_jwt


class AuthService:

    @staticmethod
    def login(username: str):

        # TEMP (replace with DB users later)
        if username == "admin":

            token = create_jwt({
                "user": username,
                "role": "admin"
            })

            return {"access_token": token}

        return None


    @staticmethod
    def verify(token: str):
        return verify_jwt(token)

    from app.core.jwt import (
    create_access_token,
    create_refresh_token,
)

access_token = create_access_token(str(user.id))
refresh_token = create_refresh_token(str(user.id))

return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    "user": {
        "id": str(user.id),
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "role": user.role,
        "active": user.active,
    },
}