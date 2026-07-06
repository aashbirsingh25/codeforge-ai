import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

logger = logging.getLogger("app.core.events")

class EventPublisher:
    """
    Sub/Pub broker managing real-time event distribution and historical event caching.
    """
    def __init__(self):
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}

    def subscribe(self, target_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        if target_id not in self._listeners:
            self._listeners[target_id] = []
        self._listeners[target_id].append(queue)
        return queue

    def unsubscribe(self, target_id: str, queue: asyncio.Queue) -> None:
        if target_id in self._listeners:
            if queue in self._listeners[target_id]:
                self._listeners[target_id].remove(queue)
            if not self._listeners[target_id]:
                del self._listeners[target_id]

    def publish(self, target_id: str, event_type: str, data: Dict[str, Any]) -> None:
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "data": data
        }
        if target_id not in self._history:
            self._history[target_id] = []
        self._history[target_id].append(event)

        if target_id in self._listeners:
            for queue in self._listeners[target_id]:
                queue.put_nowait(event)

    def get_history(self, target_id: str) -> List[Dict[str, Any]]:
        return self._history.get(target_id, [])

    def clear_history(self, target_id: str) -> None:
        if target_id in self._history:
            del self._history[target_id]

# Global event publisher instance
event_publisher = EventPublisher()
