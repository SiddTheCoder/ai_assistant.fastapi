# app/core/execution_engine.py
"""
Execution Engine - The Missing Piece!

This is the continuous loop that:
1. Monitors ExecutionState per user
2. Fetches executable batches
3. Executes server tasks in parallel
4. Emits client tasks via WebSocket
5. Waits for completion and loops
"""

import asyncio
import logging
from typing import Dict, Optional, Set
from datetime import datetime

from app.core.orchestrator import get_orchestrator
from app.core.models import TaskRecord, TaskOutput

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Per-user execution engine that runs in background
    
    Each user gets their own engine instance when they send a message
    Engine lives until all tasks are complete or timeout
    """
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        
        # Track running engines per user
        self.running_engines: Dict[str, asyncio.Task] = {}
        
        # Tool executors (will be injected)
        self.server_tool_executor = None
        self.client_task_emitter = None
        
        logger.info("✅ Execution Engine initialized")
    
    def set_server_executor(self, executor):
        """Inject server tool executor"""
        self.server_tool_executor = executor
    
    def set_client_emitter(self, emitter):
        """Inject client task emitter"""
        self.client_task_emitter = emitter
    
    async def start_execution(self, user_id: str) -> asyncio.Task:
        """
        Start execution engine for a user (non-blocking)
        
        This is called after orchestrator.register_tasks()
        Creates a background task that runs the execution loop
        """
        # Check if already running for this user
        if user_id in self.running_engines:
            existing = self.running_engines[user_id]
            if not existing.done():
                logger.info(f"⚠️  Execution already running for {user_id}")
                return existing
        
        # Start new background task
        task = asyncio.create_task(
            self._execution_loop(user_id)
        )
        self.running_engines[user_id] = task
        
        logger.info(f"🚀 Started execution engine for user: {user_id}")

        return task
    
    async def _execution_loop(self, user_id: str) -> None:
        """
        Main execution loop for a user
        
        This runs continuously until all tasks are done or timeout
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🔥 EXECUTION LOOP STARTED: {user_id}")
        logger.info(f"{'='*70}\n")
        
        iteration = 0
        max_iterations = 100  # Safety limit
        no_work_count = 0
        max_idle = 5  # Exit after 5 iterations with no work
        
        try:
            while iteration < max_iterations:
                iteration += 1
                
                logger.info(f"\n{'─'*70}")
                logger.info(f"Iteration {iteration} - User: {user_id}")
                logger.info(f"{'─'*70}")
                
                # 1. Get executable batch
                batch = await self.orchestrator.get_executable_batch(user_id)
                
                has_work = bool(batch.server_tasks or batch.client_tasks)
                
                if not has_work:
                    no_work_count += 1
                    logger.info(f"⏸️  No runnable tasks (idle count: {no_work_count}/{max_idle})")
                    
                    if no_work_count >= max_idle:
                        # Check if there are still pending tasks (waiting on dependencies)
                        state = self.orchestrator.get_state(user_id)
                        if state:
                            pending = state.get_tasks_by_status("pending")
                            running = state.get_tasks_by_status("running")
                            
                            if pending or running:
                                logger.info(f"⏳ Still have {len(pending)} pending, {len(running)} running")
                                logger.info(f"⏳ Tasks still pending/running, continuing...")
                                no_work_count = 0  # Reset
                                await asyncio.sleep(1)
                                continue
                        
                        logger.info("✅ No more work - execution complete!")
                        break
                    
                    await asyncio.sleep(0.5)
                    continue
                
                # Reset idle counter
                no_work_count = 0
                
                logger.info(f"📦 Batch: {len(batch.server_tasks)} server, {len(batch.client_tasks)} client")
                
                # 2. Execute server tasks in PARALLEL
                if batch.server_tasks:
                    logger.info(f"\n🚀 Executing {len(batch.server_tasks)} server tasks in parallel...")
                    await self._execute_server_batch(user_id, batch.server_tasks)
                
                # 3. Emit client tasks
                if batch.client_tasks:
                    logger.info(f"\n📤 Emitting {len(batch.client_tasks)} client tasks...")
                    await self._emit_client_batch(user_id, batch.client_tasks)
                
                # 4. Small delay before next iteration
                await asyncio.sleep(0.3)
            
            if iteration >= max_iterations:
                logger.warning(f"⚠️  Max iterations reached for {user_id}")
        
        except Exception as e:
            logger.error(f"❌ Execution loop error for {user_id}: {e}")
        
        finally:
            # Cleanup
            if user_id in self.running_engines:
                del self.running_engines[user_id]
            
            # Print final summary
            await self._print_final_summary(user_id)
            
            logger.info(f"\n{'='*70}")
            logger.info(f"🏁 EXECUTION LOOP ENDED: {user_id}")
            logger.info(f"{'='*70}\n")
    
    async def _execute_server_batch(self, user_id: str, tasks: list[TaskRecord]) -> None:
        """
        Execute multiple server tasks in parallel
        
        ✅ Uses REAL ServerToolExecutor (injected at startup)
        Each task calls actual tool adapters (web_search, api_call, etc.)
        """
        if not self.server_tool_executor:
            logger.error("❌ No server tool executor configured!")
            return
        
        # Execute all tasks in parallel
        results = await asyncio.gather(
            *[self._execute_single_server_task(user_id, task) for task in tasks],
            return_exceptions=True
        )
        
        # Log results
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"✅ Completed {success_count}/{len(tasks)} server tasks")
    
    async def _execute_single_server_task(self, user_id: str, task: TaskRecord) -> None:
        """Execute a single server task"""
        try:
            # Mark as running
            await self.orchestrator.mark_task_running(user_id, task.task_id)
            
            logger.info(f"  🔄 Executing: {task.task_id} ({task.tool})")
            
            # Show lifecycle message
            if task.lifecycle_messages and task.lifecycle_messages.on_start:
                logger.info(f"     💬 {task.lifecycle_messages.on_start}")

            # Check if executor is available 
            if not self.server_tool_executor: 
                raise RuntimeError("Server tool executor not configured")    
            
            # Get timeout
            timeout = None
            if task.control and task.control.timeout_ms:
                timeout = task.control.timeout_ms / 1000
            
            # ✅ Execute the tool using REAL ServerToolExecutor
            # This calls the actual tool adapters (web_search, etc.)
            if timeout:
                output = await asyncio.wait_for(
                    self.server_tool_executor.execute(task),  # ← REAL executor!
                    timeout=timeout
                )
            else:
                output = await self.server_tool_executor.execute(task)  # ← REAL executor!
            
            # Mark completed
            await self.orchestrator.mark_task_completed(user_id, task.task_id, output)
            #TODO : I need to implement the input bindings here i guess or might be in the orchestrator after any task get completedt
            
            # Show success message
            if task.lifecycle_messages and task.lifecycle_messages.on_success:
                logger.info(f"     💬 {task.lifecycle_messages.on_success}")
            
            logger.info(f"  ✅ Completed: {task.task_id} ({task.duration_ms}ms)")
        
        except asyncio.TimeoutError:
            error = f"Task timed out after {timeout}s" # type: ignore
            await self.orchestrator.mark_task_failed(user_id, task.task_id, error)
            
            if task.lifecycle_messages and task.lifecycle_messages.on_failure:
                logger.info(f"     💬 {task.lifecycle_messages.on_failure}")
        
        except Exception as e:
            error = str(e)
            await self.orchestrator.mark_task_failed(user_id, task.task_id, error)
            
            if task.lifecycle_messages and task.lifecycle_messages.on_failure:
                logger.info(f"     💬 {task.lifecycle_messages.on_failure}")
    
    async def _emit_client_batch(self, user_id: str, tasks: list[TaskRecord]) -> None:
        """
        Emit client tasks in batches
        
        SMART BATCHING:
        - If tasks are independent → Emit separately (parallel on client)
        - If tasks are chained (A→B→C all client) → Emit as batch (client handles locally)
        
        This makes client execution snappy!
        """
        if not self.client_task_emitter:
            logger.error("❌ No client task emitter configured!")
            # MARK TASKS AS FAILED!
            for task in tasks:
                await self.orchestrator.mark_task_failed(
                    user_id,
                    task.task_id,
                    "Client task emitter not configured"
                )
            return 
        
        # Group tasks by dependency chains
        independent_tasks = []
        chained_batches = self._group_chained_tasks(tasks)
        
        # Emit chained batches (client handles dependencies locally)
        for chain in chained_batches:
            if len(chain) > 1:
                logger.info(f"  📦 Emitting chained batch: {[t.task_id for t in chain]}")
                await self.client_task_emitter.emit_task_batch(user_id, chain)
            else:
                independent_tasks.extend(chain)
        
        # Emit independent tasks separately
        for task in independent_tasks:
            try:
                if task.lifecycle_messages and task.lifecycle_messages.on_start:
                    logger.info(f"     💬 {task.lifecycle_messages.on_start}")
                
                success = await self.client_task_emitter.emit_task_single(user_id, task)
                
                if success:
                    logger.info(f"  📤 Emitted: {task.task_id} ({task.tool})")
                else:
                    logger.warning(f"  ⚠️  Failed to emit: {task.task_id}")
            
            except Exception as e:
                logger.error(f"  ❌ Error emitting {task.task_id}: {e}")
    
    def _group_chained_tasks(self, tasks: list[TaskRecord]) -> list[list[TaskRecord]]:
        """
        Group tasks by dependency chains
        
        Example:
        - task1 (no deps)
        - task2 (depends on task1)
        - task3 (depends on task2)
        
        Returns: [[task1, task2, task3]]
        
        This allows client to handle entire chain locally!
        """
        if not tasks:
            return []
        
        chains = []
        task_map = {t.task_id: t for t in tasks}
        processed = set()
        
        for task in tasks:
            if task.task_id in processed:
                continue
            
            # Build chain starting from this task
            chain = [task]
            processed.add(task.task_id)
            
            # Look for tasks that depend on this one
            current_id = task.task_id
            while True:
                found_dependent = False
                for other_task in tasks:
                    if other_task.task_id not in processed:
                        if current_id in other_task.depends_on:
                            chain.append(other_task)
                            processed.add(other_task.task_id)
                            current_id = other_task.task_id
                            found_dependent = True
                            break
                
                if not found_dependent:
                    break
            
            chains.append(chain)
        
        return chains
    
    async def _print_final_summary(self, user_id: str):
        """Print execution summary at the end"""
        summary = await self.orchestrator.get_execution_summary(user_id)
        
        logger.info("\n" + "="*70)
        logger.info("FINAL EXECUTION SUMMARY")
        logger.info("="*70)
        logger.info(f"User:        {user_id}")
        logger.info(f"Total Tasks: {summary['total']}")
        logger.info(f"✅ Completed: {summary['completed']}")
        logger.info(f"❌ Failed:    {summary['failed']}")
        logger.info(f"⏳ Pending:   {summary['pending']}")
        logger.info(f"🔄 Running:   {summary['running']}")
        
        if summary['total'] > 0:
            success_rate = (summary['completed'] / summary['total']) * 100
            logger.info(f"Success Rate: {success_rate:.1f}%")
        
        logger.info("="*70)
    
    def is_running(self, user_id: str) -> bool:
        """Check if execution is running for user"""
        task = self.running_engines.get(user_id)
        return task is not None and not task.done()
    
    async def stop_execution(self, user_id: str) -> None:
        """Stop execution for a user (graceful shutdown)"""
        task = self.running_engines.get(user_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"🛑 Stopped execution for {user_id}")


# Global singleton
_execution_engine: Optional[ExecutionEngine] = None


def get_execution_engine() -> ExecutionEngine:
    """Get global execution engine instance"""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine


def init_execution_engine() -> ExecutionEngine:
    """Initialize execution engine at startup"""
    global _execution_engine
    _execution_engine = ExecutionEngine()
    return _execution_engine