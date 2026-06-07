from app.websocket.router import manager

class EventStream:

    @staticmethod
    async def publish(event: dict):

        enriched_event = {
            "type": event.get("type"),
            "device_id": event.get("device_id"),
            "severity": event.get("severity"),
            "payload": event.get("payload"),
        }

        await manager.broadcast(enriched_event)