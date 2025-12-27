# app/socket/task_handler.py
"""
WebSocket Task Handler
Handles task emission to clients and result acknowledgment
"""

import logging
from typing import Dict, Any
import socketio

from app.core.orchestrator import get_orchestrator
from app.core.models import Task, TaskOutput, TaskRecord

logger = logging.getLogger(__name__)


class SocketTaskHandler:
    """
    Handles task-related WebSocket events
    """
    
    def __init__(self, sio: socketio.AsyncServer, connected_users: Dict[str, set]):
        self.sio = sio
        self.connected_users = connected_users
        self.orchestrator = get_orchestrator()
    
    async def emit_task_to_client(self, user_id: str, task: TaskRecord) -> bool:
        """
        Emit a task to the client for execution
        
        Args:
            user_id: User identifier
            task: TaskRecord to execute on client
            
        Returns:
            True if emitted successfully
        """
        # Check if user is connected
        if user_id not in self.connected_users or not self.connected_users[user_id]:
            logger.warning(f"⚠️  User {user_id} not connected - cannot emit task {task.task_id}")
            return False
        
        # Get one of the user's socket IDs
        sid = next(iter(self.connected_users[user_id]))
        
        # ✅ Prepare FULL task payload - client gets EVERYTHING
        payload = {
            # Complete task definition
            "task_id": task.task_id,
            "tool": task.tool,
            "execution_target": task.execution_target,
            "depends_on": task.depends_on,
            
            # Inputs (both static and resolved)
            "inputs": task.task.inputs,  # Original static inputs
            "resolved_inputs": task.resolved_inputs,  # After binding resolution
            "input_bindings": task.task.input_bindings,  # For client-side resolution if needed
            
            # ✅ Lifecycle messages - client can show these to user!
            "lifecycle_messages": task.lifecycle_messages.dict() if task.lifecycle_messages else None,
            
            # ✅ Control settings - client respects these!
            "control": task.control.dict() if task.control else None,
            
            # Metadata
            "created_at": task.created_at.isoformat()
        }
        
        try:
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
    
    async def emit_batch_to_client(self, user_id: str, tasks: list[TaskRecord]) -> int:
        """
        Emit multiple tasks to client
        
        Returns:
            Number of successfully emitted tasks
        """
        success_count = 0
        
        for task in tasks:
            if await self.emit_task_to_client(user_id, task):
                success_count += 1
        
        logger.info(f"📤 Emitted {success_count}/{len(tasks)} tasks to {user_id}")
        return success_count
    
    async def handle_task_result(
        self, 
        user_id: str, 
        task_id: str, 
        result: Dict[str, Any]
    ) -> None:
        """
        Handle task result from client
        
        Args:
            user_id: User identifier
            task_id: Task that completed
            result: Result data from client
        """
        try:
            # Parse result into TaskOutput
            output = TaskOutput(
                success=result.get("success", False),
                data=result.get("data", {}),
                error=result.get("error")
            )
            
            # Update orchestrator
            await self.orchestrator.handle_client_ack(user_id, task_id, output)
            
            logger.info(f"✅ Received result for task {task_id} from {user_id}")
            
            # Notify user via socket
            await self.notify_task_status(user_id, task_id, "completed" if output.success else "failed")
            
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
        Notify user about task status change
        
        Args:
            user_id: User identifier
            task_id: Task ID
            status: New status
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
    
    async def get_task_status(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """
        Get current task status
        
        Returns:
            Task status information
        """
        task = self.orchestrator.get_task(user_id, task_id)
        
        if not task:
            return {
                "found": False,
                "error": "Task not found"
            }
        
        return {
            "found": True,
            "task_id": task.task_id,
            "tool": task.tool,
            "status": task.status,
            "execution_target": task.execution_target,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration_ms": task.duration_ms,
            "error": task.error
        }


# Example Socket.IO event handlers
async def register_task_events(
    sio: socketio.AsyncServer, 
    connected_users: Dict[str, set]
):
    """
    Register task-related socket events
    Call this in your socket_server.py
    """
    handler = SocketTaskHandler(sio, connected_users)
    
    @sio.on("task:result") # type: ignore
    async def handle_task_result(sid: str, data: Dict[str, Any]):
        """Client sends task execution result"""
        try:
            # Get user_id from session (you need to implement this)
            # For now, assuming data contains user_id
            user_id = data.get("user_id")
            task_id = data.get("task_id")
            result = data.get("result", {})
            
            if not user_id or not task_id:
                logger.error("Missing user_id or task_id in task result")
                return
            
            await handler.handle_task_result(user_id, task_id, result)
            
        except Exception as e:
            logger.error(f"Error handling task result: {e}")
    
    @sio.on("task:status_request") # type: ignore
    async def handle_status_request(sid: str, data: Dict[str, Any]):
        """Client requests task status"""
        try:
            user_id = data.get("user_id")
            task_id = data.get("task_id")
            
            if not user_id or not task_id:
                return {"error": "Missing user_id or task_id"}
            
            status = await handler.get_task_status(user_id, task_id)
            
            await sio.emit("task:status_response", status, room=sid)
            
        except Exception as e:
            logger.error(f"Error handling status request: {e}")
    
    logger.info("✅ Task event handlers registered")
    
    # Return handler for dependency injection into execution engine
    return handler


# Export for use in other modules
def get_task_handler(
    sio: socketio.AsyncServer, 
    connected_users: Dict[str, set]
) -> SocketTaskHandler:
    """Get or create task handler"""
    return SocketTaskHandler(sio, connected_users)