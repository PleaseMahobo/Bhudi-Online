class RulesEngine:
    def __init__(self):
        self.failed_logins = {}

    def evaluate(self, event: dict):
        device = event["device_id"]

        # RULE 1: repeated failures
        if event["type"] == "alert" and event["payload"].get("code") == "LOGIN_FAIL":

            self.failed_logins[device] = self.failed_logins.get(device, 0) + 1

            if self.failed_logins[device] >= 3:
                return {
                    "type": "incident",
                    "severity": "high",
                    "title": "Possible brute force detected",
                    "device_id": device
                }

        # RULE 2: offline + alerts = critical
        if event["type"] == "heartbeat" and event["payload"].get("status") == "offline":
            return {
                "type": "incident",
                "severity": "critical",
                "title": "Device went offline",
                "device_id": device
            }

        return None