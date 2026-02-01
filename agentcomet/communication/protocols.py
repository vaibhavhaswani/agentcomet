from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import uuid
from datetime import datetime

@dataclass
class Message:
    """
    Standard message protocol for agent communication.
    """
    sender: str
    receiver: str
    content: Any
    msg_type: str = "default"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)
