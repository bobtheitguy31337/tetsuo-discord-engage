from abc import ABC, abstractmethod
from typing import Optional, Dict

class MessageInterface(ABC):
    """Abstract interface for sending messages across different platforms"""
    @abstractmethod
    async def send_message(self, channel_id: str, content: str, embed: Optional[Dict] = None) -> None:
        pass
    
    @abstractmethod
    async def edit_message(self, channel_id: str, message_id: str, content: str, embed: Optional[Dict] = None) -> None:
        pass
    
    @abstractmethod
    async def delete_message(self, channel_id: str, message_id: str) -> None:
        pass