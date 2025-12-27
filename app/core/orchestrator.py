# app/core/orchestrator.py
"""
Production-Grade Task Orchestrator
- User-wise state management
- Dependency analysis
- Parallel execution support
- Server/Client task routing
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

from app.core.models import (
    Task, TaskRecord, ExecutionState, TaskStatus, 
    TaskOutput, TaskBatch, ExecutionTarget
)
from app.registry.loader import get_tool_registry

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """
    Central orchestrator managing task execution across users
    
    Responsibilities:
    - Accept task plans from LLM
    - Store per-user execution state
    - Analyze dependencies
    - Route server/client tasks
    - Coordinate parallel execution
    """
    
    def __init__(self):
        # User-wise state storage
        self.states: Dict[str, ExecutionState] = {}
        
        # Tool registry (loaded at startup)
        self.tool_registry = get_tool_registry()
        
        # Locks for thread-safe operations
        self._locks: Dict[str, asyncio.Lock] = {}
        
        logger.info("✅ TaskOrchestrator initialized")
    
    def _get_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create lock for user"""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]
    
    async def register_tasks(self, user_id: str, tasks: List[Task]) -> None:
        """
        Register a list of tasks for a user
        
        Args:
            user_id: User identifier
            tasks: List of Task objects from LLM
        """
        async with self._get_lock(user_id):
            # Create or get user state
            if user_id not in self.states:
                self.states[user_id] = ExecutionState(user_id=user_id)
                logger.info(f"📝 Created new execution state for user: {user_id}")
            
            state = self.states[user_id]
            
            logger.info(f"📥 Registering {len(tasks)} tasks for user {user_id}")
            
            for task in tasks:
                # Validate tool exists
                if not self.tool_registry.validate_tool(task.tool):
                    logger.error(f"❌ Invalid tool: {task.tool}")
                    # Create failed task record (still store full task)
                    record = TaskRecord(
                        task=task,  # ✅ Store complete Task
                        status="failed",
                        error=f"Tool '{task.tool}' not found in registry"
                    )
                else:
                    # Create task record with full task data
                    record = TaskRecord(
                        task=task,  # ✅ Store complete Task - client gets EVERYTHING
                        status="pending"
                    )
                    logger.info(f"  ✅ {task.task_id}: {task.tool} [{task.execution_target}]")
                
                state.add_task(record)
            
            logger.info(f"✅ Registered {len(tasks)} tasks for user {user_id}")
    
    async def get_executable_batch(self, user_id: str) -> TaskBatch:
        """
        Get batch of tasks ready to execute
        
        Returns:
            TaskBatch with separate lists for server and client tasks
        """
        async with self._get_lock(user_id):
            state = self.states.get(user_id)
            
            if not state:
                return TaskBatch()
            
            batch = TaskBatch()
            
            # Find all pending tasks
            pending_tasks = state.get_tasks_by_status("pending")
            
            for task in pending_tasks:
                # Check if dependencies are met
                if self._are_dependencies_met(state, task.task_id):
                    # Route by execution target
                    if task.execution_target == "server":
                        batch.server_tasks.append(task)
                    elif task.execution_target == "client":
                        batch.client_tasks.append(task)
            
            logger.info(
                f"📦 Batch for {user_id}: "
                f"{len(batch.server_tasks)} server, "
                f"{len(batch.client_tasks)} client"
            )
            
            return batch
    
    def _are_dependencies_met(self, state: ExecutionState, task_id: str) -> bool:
        """
        Check if all dependencies for a task are completed
        
        Args:
            state: User execution state
            task_id: Task to check
            
        Returns:
            True if all dependencies are completed
        """
        task = state.get_task(task_id)
        
        if not task or not task.depends_on:
            return True
        
        completed_ids = state.get_completed_task_ids()
        
        for dep_id in task.depends_on:
            if dep_id not in completed_ids:
                return False
        
        return True
    
    async def mark_task_running(self, user_id: str, task_id: str) -> None:
        """Mark task as running"""
        async with self._get_lock(user_id):
            state = self.states.get(user_id)
            if not state:
                return
            
            task = state.get_task(task_id)
            if task:
                task.status = "running"
                task.started_at = datetime.now()
                state.updated_at = datetime.now()
                logger.info(f"🔄 [{user_id}] Task {task_id} started")
    
    async def mark_task_completed(
        self, 
        user_id: str, 
        task_id: str, 
        output: TaskOutput
    ) -> None:
        """Mark task as completed with output"""
        async with self._get_lock(user_id):
            state = self.states.get(user_id)
            if not state:
                return
            
            task = state.get_task(task_id)
            if task:
                task.status = "completed"
                task.output = output
                task.completed_at = datetime.now()
                
                if task.started_at:
                    duration = (task.completed_at - task.started_at).total_seconds() * 1000
                    task.duration_ms = int(duration)
                
                state.updated_at = datetime.now()
                logger.info(f"✅ [{user_id}] Task {task_id} completed in {task.duration_ms}ms")
    
    async def mark_task_failed(
        self, 
        user_id: str, 
        task_id: str, 
        error: str
    ) -> None:
        """Mark task as failed"""
        async with self._get_lock(user_id):
            state = self.states.get(user_id)
            if not state:
                return
            
            task = state.get_task(task_id)
            if task:
                task.status = "failed"
                task.error = error
                task.completed_at = datetime.now()
                
                if task.started_at:
                    duration = (task.completed_at - task.started_at).total_seconds() * 1000
                    task.duration_ms = int(duration)
                
                state.updated_at = datetime.now()
                logger.error(f"❌ [{user_id}] Task {task_id} failed: {error}")
    
    async def mark_task_emitted(self, user_id: str, task_id: str) -> None:
        """Mark client task as emitted to client"""
        async with self._get_lock(user_id):
            state = self.states.get(user_id)
            if not state:
                return
            
            task = state.get_task(task_id)
            if task:
                task.status = "running"
                task.emitted_at = datetime.now()
                task.started_at = datetime.now()
                state.updated_at = datetime.now()
                logger.info(f"📤 [{user_id}] Task {task_id} emitted to client")
    
    async def handle_client_ack(
        self, 
        user_id: str, 
        task_id: str, 
        output: TaskOutput
    ) -> None:
        """Handle acknowledgment from client with results"""
        async with self._get_lock(user_id):
            state = self.states.get(user_id)
            if not state:
                return
            
            task = state.get_task(task_id)
            if task:
                task.ack_received_at = datetime.now()
                
                if output.success:
                    await self.mark_task_completed(user_id, task_id, output)
                else:
                    error = output.error or "Client execution failed"
                    await self.mark_task_failed(user_id, task_id, error)
    
    def get_state(self, user_id: str) -> Optional[ExecutionState]:
        """Get user execution state"""
        return self.states.get(user_id)
    
    def get_task(self, user_id: str, task_id: str) -> Optional[TaskRecord]:
        """Get specific task for user"""
        state = self.states.get(user_id)
        return state.get_task(task_id) if state else None
    
    async def get_execution_summary(self, user_id: str) -> Dict[str, int]:
        """Get execution summary for user"""
        async with self._get_lock(user_id):
            state = self.states.get(user_id)
            
            if not state:
                return {
                    "total": 0,
                    "pending": 0,
                    "running": 0,
                    "completed": 0,
                    "failed": 0
                }
            
            summary = {
                "total": len(state.tasks),
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "waiting": 0
            }
            
            for task in state.tasks.values():
                summary[task.status] += 1
            
            return summary
    
    async def cleanup_user_state(self, user_id: str) -> None:
        """Cleanup user state (call on disconnect)"""
        async with self._get_lock(user_id):
            if user_id in self.states:
                del self.states[user_id]
                logger.info(f"🧹 Cleaned up state for user: {user_id}")
            
            if user_id in self._locks:
                del self._locks[user_id]


# Global orchestrator instance
_orchestrator: Optional[TaskOrchestrator] = None


def get_orchestrator() -> TaskOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskOrchestrator()
    return _orchestrator


def init_orchestrator() -> TaskOrchestrator:
    """Initialize orchestrator at startup"""
    global _orchestrator
    _orchestrator = TaskOrchestrator()
    return _orchestrator