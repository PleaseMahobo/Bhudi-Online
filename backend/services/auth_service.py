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