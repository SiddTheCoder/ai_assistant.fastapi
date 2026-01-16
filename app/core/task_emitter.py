# app/core/task_emitter.py
"""
Task Emitter - Fake WebSocket for Development

Emits tasks directly to client_core_demo instead of via WebSocket.
Acts as a drop-in replacement for SocketTaskHandler during development.

Usage:
    from app.core.task_emitter import get_task_emitter
    
    emitter = get_task_emitter()
    await emitter.emit_task_batch(user_id, tasks)
"""

import logging
from typing import List, Callable, Awaitable, Optional

from app.core.models import TaskRecord
from app.core.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)


# Type for the callback function
TaskCallback = Callable[[str, List[dict]], Awaitable[None]]


class TaskEmitter:
    """
    Fake WebSocket task emitter for development.
    
    Instead of sending tasks over WebSocket, directly calls
    client_core_demo.main.receive_tasks_from_server().
    
    Implements same interface as SocketTaskHandler for seamless swapping:
    - emit_task_single(user_id, task) -> bool
    - emit_task_batch(user_id, tasks) -> bool
    """
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self._client_callback: Optional[TaskCallback] = None
        
        logger.info("✅ Task Emitter initialized (fake WebSocket mode)")
    
    def set_client_callback(self, callback: TaskCallback) -> None:
        """
        Set the callback function to receive tasks.
        
        Args:
            callback: Async function with signature:
                      async def callback(user_id: str, tasks: List[dict]) -> None
        """
        self._client_callback = callback
        logger.info("✅ Client callback registered")
    
    async def emit_task_single(self, user_id: str, task: TaskRecord) -> bool:
        """
        Emit single task to client.
        
        Serializes TaskRecord to JSON dict and calls client callback.
        Always sends as list for consistent interface.
        
        Args:
            user_id: User ID
            task: TaskRecord to emit
            
        Returns:
            True if emission successful
        """
        try:
            if not self._client_callback:
                logger.error("❌ No client callback configured!")
                return False
            
            # Mark as emitted on server side
            await self.orchestrator.mark_task_emitted(user_id, task.task_id)
            
            # Serialize to JSON dict (like WebSocket would do)
            task_dict = task.model_dump(mode='json')
            
            # Send to client as list (consistent interface)
            await self._client_callback(user_id, [task_dict])
            
            logger.info(f"📤 Emitted task {task.task_id} to client")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to emit task {task.task_id}: {e}")
            return False
    
    async def emit_task_batch(self, user_id: str, tasks: List[TaskRecord]) -> bool:
        """
        Emit batch of tasks to client.
        
        Serializes all TaskRecords to JSON dicts and calls client callback.
        
        Args:
            user_id: User ID
            tasks: List of TaskRecords to emit
            
        Returns:
            True if emission successful
        """
        try:
            if not self._client_callback:
                logger.error("❌ No client callback configured!")
                return False
            
            # Mark all as emitted on server side
            for task in tasks:
                await self.orchestrator.mark_task_emitted(user_id, task.task_id)
            
            # Serialize all to JSON dicts
            task_dicts = [task.model_dump(mode='json') for task in tasks]
            
            # Send entire batch to client
            await self._client_callback(user_id, task_dicts)
            
            logger.info(f"📦 Emitted batch of {len(tasks)} tasks to client")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to emit batch: {e}")
            return False


# Global singleton
_task_emitter: Optional[TaskEmitter] = None


def get_task_emitter() -> TaskEmitter:
    """Get global task emitter instance."""
    global _task_emitter
    if _task_emitter is None:
        _task_emitter = TaskEmitter()
    return _task_emitter


def init_task_emitter() -> TaskEmitter:
    """Initialize task emitter at startup."""
    global _task_emitter
    _task_emitter = TaskEmitter()
    return _task_emitter


def setup_client_demo_emitter() -> TaskEmitter:
    """
    Setup task emitter with client_core_demo callback.
    
    Convenience function to wire up the emitter with client callback.
    
    Usage:
        from app.core.task_emitter import setup_client_demo_emitter
        
        emitter = setup_client_demo_emitter()
        # Now emitter will send tasks to client_core_demo
    """
    from app.client_core.main import receive_tasks_from_server
    
    emitter = get_task_emitter()
    emitter.set_client_callback(receive_tasks_from_server)
    
    logger.info("✅ Task Emitter wired to client_core_demo")
    return emitter
