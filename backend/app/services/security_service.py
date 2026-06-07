from app.core.security import verify_api_key


class SecurityService:

    @staticmethod
    def validate_agent(api_key: str, device):
        if not device:
            return False

        if not device.api_key_hash:
            return False

        return verify_api_key(api_key, device.api_key_hash)