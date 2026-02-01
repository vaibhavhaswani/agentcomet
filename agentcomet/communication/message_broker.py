from typing import Dict, List, Callable, Optional
from .protocols import Message
import collections

class MessageBroker:
    """
    Handles message passing between agents.
    """
    def __init__(self):
        self._queues: Dict[str, collections.deque] = collections.defaultdict(collections.deque)
        self._subscribers: Dict[str, List[Callable[[Message], None]]] = collections.defaultdict(list)

    def send(self, message: Message):
        """
        Send a message to a specific receiver.
        """
        self._queues[message.receiver].append(message)
        # Notify subscribers immediately
        for callback in self._subscribers.get(message.receiver, []):
            try:
                callback(message)
            except Exception as e:
                print(f"Error in subscriber callback for {message.receiver}: {e}")

    def subscribe(self, agent_name: str, callback: Callable[[Message], None]):
        """
        Subscribe an agent (or callback) to messages directed at it.
        """
        self._subscribers[agent_name].append(callback)

    def receive(self, agent_name: str) -> Optional[Message]:
        """
        Get the next message for an agent from the queue.
        """
        if self._queues[agent_name]:
            return self._queues[agent_name].popleft()
        return None

    def get_all_messages(self, agent_name: str) -> List[Message]:
        """
        Get all pending messages for an agent.
        """
        messages = list(self._queues[agent_name])
        self._queues[agent_name].clear()
        return messages
