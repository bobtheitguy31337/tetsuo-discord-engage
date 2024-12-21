from typing import Callable, Dict, List
import asyncio

class EventBus:
    """Simple event bus for whale trade events"""
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        
    def on(self, event: str, handler: Callable):
        """Register an event handler"""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
        
    async def emit(self, event: str, data):
        """Emit an event to all registered handlers"""
        if event not in self._handlers:
            return
            
        for handler in self._handlers[event]:
            try:
                await handler(data)
            except Exception as e:
                print(f"Error in event handler: {e}")