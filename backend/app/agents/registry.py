from datetime import datetime, timedelta, timezone

AGENT_REGISTRY = {}

class AgentRegistry:

    @staticmethod
    def update(agent_id: str, data: dict):
        AGENT_REGISTRY[agent_id] = {
            **data,
            "last_seen": datetime.now(timezone.utc)
        }

    @staticmethod
    def get(agent_id: str):
        return AGENT_REGISTRY.get(agent_id)

    @staticmethod
    def get_all():
        return AGENT_REGISTRY