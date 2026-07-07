class AuthService:

    @staticmethod
    def login(email: str, password: str):
        # Temporary admin account
        if email == "admin@bhudi.com" and password == "admin123":
            return {
                "id": "1",
                "email": email,
                "firstName": "BHUDI",
                "lastName": "Administrator",
                "role": "admin",
                "active": True
            }
        return None