import hashlib
import json


SECRET = "RMM_INTERNAL_SECRET"


class CommandSecurity:

    def sign_command(self, command: dict):
        payload = json.dumps(command, sort_keys=True)
        return hashlib.sha256((payload + SECRET).encode()).hexdigest()

    def verify_command(self, command: dict, signature: str):
        expected = self.sign_command(command)
        return expected == signature