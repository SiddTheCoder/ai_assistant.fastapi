# app/socket/task_handler.py
"""
WebSocket Task Handler - Real Production Version

Emits FULL TaskRecord to client for maximum flexibility
Client gets same data access as server orchestrator
"""

import logging
from typing import Dict, Any, List
import socketio

from app.core.orchestrator import get_orchestrator
from app.core.models import TaskOutput, TaskRecord

logger = logging.getLogger(__name__)


class SocketTaskHandler:
    """
    Production WebSocket task handler
    
    Emits complete TaskRecord to client - client orchestrator 
    has same level of access as server orchestrator
    """
    
    def __init__(self, sio: socketio.AsyncServer, connected_users: Dict[str, set]):
        self.sio = sio
        self.connected_users = connected_users
        self.orchestrator = get_orchestrator()
    
    async def emit_task_single(self, user_id: str, task: TaskRecord) -> bool:
        """
        Emit single task to client
        
        ✅ Sends COMPLETE TaskRecord as JSON
        Client deserializes into its own TaskRecord model
        """
        # Check if user is connected
        if user_id not in self.connected_users or not self.connected_users[user_id]:
            logger.warning(f"⚠️  User {user_id} not connected - cannot emit task {task.task_id}")
            return False
        
        # Get one of the user's socket IDs
        sid = next(iter(self.connected_users[user_id]))
        
        try:
            # ✅ Send ENTIRE TaskRecord as JSON
            # Client gets same data as server orchestrator!
            payload = task.model_dump(mode='json')
            
            # Emit to client
            await self.sio.emit(
                "task:execute",
                payload,
                room=sid
            )
            
            # Mark as emitted
            await self.orchestrator.mark_task_emitted(user_id, task.task_id)
            
            logger.info(f"📤 Emitted task {task.task_id} to client {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to emit task {task.task_id}: {e}")
            return False
    
    async def emit_task_batch(self, user_id: str, tasks: List[TaskRecord]) -> bool:
        """
        Emit batch of tasks to client (for chains)
        
        ✅ Client receives entire chain and handles dependencies locally
        This is MUCH faster than individual emissions!
        """
        # Check if user is connected
        if user_id not in self.connected_users or not self.connected_users[user_id]:
            logger.warning(f"⚠️  User {user_id} not connected - cannot emit batch")
            return False
        
        sid = next(iter(self.connected_users[user_id]))
        
        try:
            # ✅ Send array of complete TaskRecords
            payload = {
                "tasks": [task.model_dump(mode='json') for task in tasks],
                "is_chain": True  # Signal to client this is a dependency chain
            }
            
            # Emit to client
            await self.sio.emit(
                "task:execute_batch",
                payload,
                room=sid
            )
            
            # Mark all as emitted
            for task in tasks:
                await self.orchestrator.mark_task_emitted(user_id, task.task_id)
            
            logger.info(f"📦 Emitted batch of {len(tasks)} tasks to client {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to emit batch: {e}")
            return False
    
    async def handle_task_result(
        self, 
        user_id: str, 
        task_id: str, 
        result: Dict[str, Any]
    ) -> None:
        """
        Handle task result acknowledgment from client
        
        Client sends back TaskOutput after execution
        """
        try:
            # Parse result into TaskOutput
            output = TaskOutput(
                success=result.get("success", False),
                data=result.get("data", {}),
                error=result.get("error")
            )
            
            # Update orchestrator (no lock needed - called from socket handler)
            await self.orchestrator.handle_client_ack(user_id, task_id, output)
            
            logger.info(f"✅ Received result for task {task_id} from {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle task result: {e}")
            await self.orchestrator.mark_task_failed(
                user_id, 
                task_id, 
                f"Failed to process client result: {str(e)}"
            )
    
    async def notify_task_status(
        self, 
        user_id: str, 
        task_id: str, 
        status: str
    ) -> None:
        """
        Notify client about task status change
        (Optional - for real-time UI updates)
        """
        if user_id not in self.connected_users:
            return
        
        payload = {
            "task_id": task_id,
            "status": status
        }
        
        # Emit to all user's connections
        for sid in self.connected_users[user_id]:
            try:
                await self.sio.emit(
                    "task:status",
                    payload,
                    room=sid
                )
            except Exception as e:
                logger.error(f"Failed to notify status: {e}")


# Socket.IO event registration
async def register_task_events(
    sio: socketio.AsyncServer, 
    connected_users: Dict[str, set]
) -> SocketTaskHandler:
    """
    Register task-related WebSocket events
    
    Returns handler for injection into execution engine
    """
    handler = SocketTaskHandler(sio, connected_users)
    
    @sio.on("task:result") #type: ignore
    async def handle_task_result(sid: str, data: Dict[str, Any]):
        """
        Client sends task execution result
        
        Expected data:
        {
            "user_id": "user_123",
            "task_id": "task_abc",
            "result": {
                "success": true,
                "data": {...},
                "error": null
            }
        }
        """
        try:
            user_id = data.get("user_id")
            task_id = data.get("task_id")
            result = data.get("result", {})
            
            if not user_id or not task_id:
                logger.error("Missing user_id or task_id in task result")
                return
            
            await handler.handle_task_result(user_id, task_id, result)
            
        except Exception as e:
            logger.error(f"Error handling task result: {e}")
    
    @sio.on("task:batch_results") #type: ignore
    async def handle_batch_results(sid: str, data: Dict[str, Any]):
        """
        Client sends results for entire batch
        
        Expected data:
        {
            "user_id": "user_123",
            "results": [
                {"task_id": "task_1", "result": {...}},
                {"task_id": "task_2", "result": {...}}
            ]
        }
        """
        try:
            user_id = data.get("user_id")
            results = data.get("results", [])
            
            for item in results:
                task_id = item.get("task_id")
                result = item.get("result", {})
                
                if task_id:
                    await handler.handle_task_result(user_id, task_id, result) #type: ignore
            
            logger.info(f"✅ Processed {len(results)} batch results from {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling batch results: {e}")
    
    logger.info("✅ Task event handlers registered")
    return handler


def get_task_handler(
    sio: socketio.AsyncServer, 
    connected_users: Dict[str, set]
) -> SocketTaskHandler:
    """Factory function to create task handler"""
    return SocketTaskHandler(sio, connected_users)