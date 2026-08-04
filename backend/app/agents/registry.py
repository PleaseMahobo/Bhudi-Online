from datetime import datetime, timedelta

AGENT_REGISTRY = {}

class AgentRegistry:

    @staticmethod
    def update(agent_id: str, data: dict):
        AGENT_REGISTRY[agent_id] = {
            **data,
            "last_seen": datetime.utcnow()
        }

    @staticmethod
    def get(agent_id: str):
        return AGENT_REGISTRY.get(agent_id)

    @staticmethod
    def get_all():
        return AGENT_REGISTRY