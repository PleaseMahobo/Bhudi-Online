from collections import defaultdict

class IncidentBuilder:
    def __init__(self):
        self.incidents = defaultdict(list)

    def add_event(self, event: dict):
        key = event["device_id"]

        self.incidents[key].append(event)

        # simple grouping threshold
        if len(self.incidents[key]) >= 3:
            return {
                "type": "incident",
                "device_id": key,
                "severity": "medium",
                "title": "Grouped anomaly detected",
                "events": self.incidents[key]
            }

        return None