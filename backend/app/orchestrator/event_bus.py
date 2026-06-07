from collections import defaultdict
from typing import Callable, Dict, List

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        self.subscribers[event_type].append(handler)

    def publish(self, event_type: str, event: dict):
        for handler in self.subscribers[event_type]:
            handler(event)