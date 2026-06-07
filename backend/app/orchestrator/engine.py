from datetime import datetime
from .event_bus import EventBus

class OrchestratorEngine:
    def __init__(self):
        self.bus = EventBus()
        self.event_buffer = []

    def ingest(self, event: dict):
        event["timestamp"] = datetime.utcnow().isoformat()

        # normalize
        normalized = self.normalize(event)

        # store
        self.event_buffer.append(normalized)

        # publish
        self.bus.publish(normalized["type"], normalized)

    def normalize(self, event: dict):
        return {
            "type": event.get("type", "unknown"),
            "device_id": event.get("device_id"),
            "severity": event.get("severity", "low"),
            "payload": event.get("payload", {}),
            "timestamp": event.get("timestamp"),
        }