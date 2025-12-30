# client/smart_orchestrator.py
"""
SMART Client-Side Orchestrator

✅ Handles entire task chains LOCALLY
✅ No round-trips for chained client tasks
✅ Updates local state
✅ Resolves dependencies internally
✅ One ACK at the end

Example:
Server emits: [create_folder, write_file (depends on create_folder)]
Client:
  1. Receives batch
  2. Executes create_folder
  3. Updates LOCAL state
  4. Checks: write_file deps met? YES!
  5. Resolves bindings from local state
  6. Executes write_file
  7. Sends ONE ACK with both results

🚀 SUPER FAST! No server round-trips!
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ClientTaskRecord:
    """Client's view of a task"""
    def __init__(self, task_data: Dict[str, Any]):
        self.task_id = task_data["task_id"]
        self.tool = task_data["tool"]
        self.execution_target = task_data["execution_target"]
        self.depends_on = task_data.get("depends_on", [])
        
        self.inputs = task_data.get("inputs", {})
        self.resolved_inputs = task_data.get("resolved_inputs", {})
        self.input_bindings = task_data.get("input_bindings", {})
        
        self.lifecycle_messages = task_data.get("lifecycle_messages", {})
        self.control = task_data.get("control", {})
        
        self.status = TaskStatus.PENDING
        self.output = None
        self.error = None
        
        self.created_at = datetime.fromisoformat(task_data["created_at"])
        self.started_at = None
        self.completed_at = None
        self.duration_ms = None


class SmartClientOrchestrator:
    """
    Smart client orchestrator that handles task chains locally
    
    KEY FEATURE: Executes chained tasks WITHOUT server round-trips!
    """
    
    def __init__(self, socket_client):
        self.socket = socket_client
        self.tasks: Dict[str, ClientTaskRecord] = {}
        self.tool_executors = self._load_tool_executors()
        logger.info("✅ Smart Client Orchestrator initialized")
    
    def _load_tool_executors(self):
        """Load client-side tool executors"""
        return {
            "open_app": self._execute_open_app,
            "close_app": self._execute_close_app,
            "file_create": self._execute_file_create,
            "folder_create": self._execute_folder_create,
            "file_search": self._execute_file_search,
        }
    
    async def receive_task_batch(self, batch_data: Dict[str, Any]):
        """
        Receive a BATCH of tasks from server
        
        ✅ SMART: Handles entire chain locally!
        
        Example batch:
        [
          {task_id: "create_folder", depends_on: []},
          {task_id: "write_file", depends_on: ["create_folder"]}
        ]
        
        Client executes BOTH locally, one ACK at end!
        """
        batch_id = batch_data["batch_id"]
        tasks_data = batch_data["tasks"]
        
        logger.info(f"\n📦 Received batch: {batch_id}")
        logger.info(f"   Tasks: {len(tasks_data)}")
        
        # Parse all tasks
        tasks = [ClientTaskRecord(task_data) for task_data in tasks_data]
        
        # Store in local state
        for task in tasks:
            self.tasks[task.task_id] = task
            logger.info(f"   - {task.task_id} ({task.tool})")
        
        # ✅ Execute the ENTIRE batch locally!
        results = await self._execute_batch_locally(tasks)
        
        # Send ONE ACK with all results
        await self._send_batch_result(batch_id, results)
    
    async def _execute_batch_locally(self, tasks: List[ClientTaskRecord]) -> Dict[str, Any]:
        """
        Execute entire task batch LOCALLY
        
        ✅ Handles dependencies internally
        ✅ No server round-trips
        ✅ Super fast!
        """
        logger.info(f"\n🚀 Executing batch locally...")
        
        results = {}
        max_iterations = 100
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Find runnable tasks
            runnable = self._get_runnable_tasks(tasks)
            
            if not runnable:
                # Check if all done
                pending = [t for t in tasks if t.status == TaskStatus.PENDING]
                running = [t for t in tasks if t.status == TaskStatus.RUNNING]
                
                if not pending and not running:
                    logger.info("✅ All tasks in batch completed!")
                    break
                
                logger.warning(f"⚠️  No runnable tasks but {len(pending)} pending")
                break
            
            logger.info(f"\n  Iteration {iteration}: {len(runnable)} runnable")
            
            # Execute runnable tasks
            for task in runnable:
                logger.info(f"    ▶️  Executing: {task.task_id}")
                
                # Resolve input bindings from LOCAL state
                resolved_inputs = self._resolve_input_bindings(task)
                
                # Execute
                result = await self._execute_task(task, resolved_inputs)
                
                # Store result
                results[task.task_id] = result
                
                logger.info(f"    ✅ Completed: {task.task_id}")
        
        return results
    
    def _get_runnable_tasks(self, tasks: List[ClientTaskRecord]) -> List[ClientTaskRecord]:
        """
        Find tasks that can run now
        
        ✅ Checks LOCAL state for dependencies
        """
        runnable = []
        
        for task in tasks:
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_met = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.depends_on
                if dep_id in self.tasks
            )
            
            if deps_met:
                runnable.append(task)
        
        return runnable
    
    def _resolve_input_bindings(self, task: ClientTaskRecord) -> Dict[str, Any]:
        """
        Resolve input bindings from LOCAL state
        
        ✅ No server needed! Uses local task outputs
        
        Example:
        task.input_bindings = {"content": "$.create_folder.output.data.path"}
        → Looks up create_folder in self.tasks
        → Extracts path from its output
        → Returns: {"content": "/path/to/folder"}
        """
        resolved = task.resolved_inputs.copy() if task.resolved_inputs else task.inputs.copy()
        
        for param_name, binding in task.input_bindings.items():
            if binding.startswith("$."):
                # Parse JSONPath: $.task_id.output.data.field
                parts = binding.split(".")
                if len(parts) >= 5:
                    source_task_id = parts[1]
                    field_path = parts[4:]  # Everything after "data"
                    
                    # Get from LOCAL state
                    source_task = self.tasks.get(source_task_id)
                    if source_task and source_task.output:
                        value = source_task.output
                        for field in field_path:
                            value = value.get(field, "")
                        
                        resolved[param_name] = value
                        logger.info(f"      🔗 Resolved {param_name} from {source_task_id}")
        
        return resolved
    
    async def _execute_task(self, task: ClientTaskRecord, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        # Show lifecycle message
        if task.lifecycle_messages.get("on_start"):
            self._show_message(task.lifecycle_messages["on_start"])
        
        try:
            # Get executor
            executor = self.tool_executors.get(task.tool)
            if not executor:
                raise Exception(f"No executor for {task.tool}")
            
            # Execute
            output = await executor(inputs)
            
            # Mark completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.duration_ms = int((task.completed_at - task.started_at).total_seconds() * 1000)
            task.output = output
            
            # Show success message
            if task.lifecycle_messages.get("on_success"):
                self._show_message(task.lifecycle_messages["on_success"])
            
            return {
                "success": True,
                "data": output,
                "duration_ms": task.duration_ms
            }
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            
            # Show failure message
            if task.lifecycle_messages.get("on_failure"):
                self._show_message(task.lifecycle_messages["on_failure"])
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _show_message(self, message: str):
        """Show message to user"""
        logger.info(f"      💬 {message}")
        # In real Electron: show notification
    
    async def _send_batch_result(self, batch_id: str, results: Dict[str, Any]):
        """
        Send batch results to server
        
        ✅ ONE ACK for entire batch!
        """
        payload = {
            "batch_id": batch_id,
            "results": results
        }
        
        logger.info(f"\n📤 Sending batch results to server")
        logger.info(f"   Batch: {batch_id}")
        logger.info(f"   Tasks: {len(results)}")
        
        await self.socket.emit("task:batch_result", payload)
    
    # ========================================
    # TOOL EXECUTORS
    # ========================================
    
    async def _execute_folder_create(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create folder"""
        path = inputs.get("path")
        logger.info(f"        📁 Creating folder: {path}")
        
        # Real implementation:
        # import os
        # os.makedirs(os.path.expanduser(path), exist_ok=True)
        
        await asyncio.sleep(0.2)  # Simulate work
        
        return {
            "folder_path": path,
            "created_at": datetime.now().isoformat()
        }
    
    async def _execute_file_create(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create file"""
        path = inputs.get("path")
        content = inputs.get("content", "")
        
        logger.info(f"        📝 Creating file: {path}")
        logger.info(f"           Content length: {len(content)} chars")
        
        # Real implementation:
        # with open(os.path.expanduser(path), 'w') as f:
        #     f.write(content)
        
        await asyncio.sleep(0.3)  # Simulate work
        
        return {
            "path": path,
            "size_bytes": len(content),
            "created_at": datetime.now().isoformat()
        }
    
    async def _execute_open_app(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Open app"""
        target = inputs.get("target")
        logger.info(f"        🚀 Opening: {target}")
        await asyncio.sleep(0.5)
        return {"process_id": 12345, "target": target}
    
    async def _execute_close_app(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Close app"""
        target = inputs.get("target")
        logger.info(f"        🛑 Closing: {target}")
        await asyncio.sleep(0.3)
        return {"exit_code": 0, "target": target}
    
    async def _execute_file_search(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Search files"""
        query = inputs.get("query")
        logger.info(f"        🔍 Searching: {query}")
        await asyncio.sleep(0.4)
        return {"results": [], "total": 0}


# ========================================
# DEMO
# ========================================

async def demo():
    """Demo showing local batch execution"""
    
    class MockSocket:
        async def emit(self, event, data):
            logger.info(f"\n📡 Socket → Server: {event}")
    
    socket = MockSocket()
    orchestrator = SmartClientOrchestrator(socket)
    
    # Simulate batch from server
    batch = {
        "batch_id": "batch_123",
        "tasks": [
            {
                "task_id": "create_folder_1",
                "tool": "folder_create",
                "execution_target": "client",
                "depends_on": [],
                "inputs": {"path": "~/Desktop/test_folder"},
                "resolved_inputs": {"path": "~/Desktop/test_folder"},
                "input_bindings": {},
                "lifecycle_messages": {
                    "on_start": "📁 Creating folder...",
                    "on_success": "✅ Folder created!"
                },
                "control": {},
                "created_at": datetime.now().isoformat()
            },
            {
                "task_id": "write_file_2",
                "tool": "file_create",
                "execution_target": "client",
                "depends_on": ["create_folder_1"],
                "inputs": {
                    "path": "~/Desktop/test_folder/file.txt",
                    "content": ""
                },
                "resolved_inputs": {},
                "input_bindings": {
                    "path": "$.create_folder_1.output.data.folder_path"
                },
                "lifecycle_messages": {
                    "on_start": "📝 Writing file...",
                    "on_success": "✅ File created!"
                },
                "control": {},
                "created_at": datetime.now().isoformat()
            }
        ]
    }
    
    logger.info("="*70)
    logger.info("SMART CLIENT BATCH EXECUTION DEMO")
    logger.info("="*70)
    
    await orchestrator.receive_task_batch(batch)
    
    logger.info("\n" + "="*70)
    logger.info("DEMO COMPLETE")
    logger.info("="*70)


if __name__ == "__main__":
    asyncio.run(demo())