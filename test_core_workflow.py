# test_complete_flow.py
"""
Test the COMPLETE flow:

1. Load tool registry
2. Initialize orchestrator + engine
3. Generate tasks
4. Register tasks
5. Start execution (background)
6. Watch it run automatically
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from app.registry.loader import load_tool_registry
from app.core.orchestrator import init_orchestrator
from app.core.execution_engine import init_execution_engine
from app.core.server_executor import init_server_executor
from app.core.models import Task


async def main():
    logger.info("\n" + "="*70)
    logger.info("COMPLETE EXECUTION FLOW TEST")
    logger.info("="*70 + "\n")
    
    # Step 1: Load tool registry
    logger.info("Step 1: Loading tool registry...")
    try:
        load_tool_registry()
        logger.info("✅ Tool registry loaded\n")
    except:
        logger.warning("⚠️  Using mock registry\n")
    
    # Step 2: Initialize components
    logger.info("Step 2: Initializing orchestration system...")
    orchestrator = init_orchestrator()
    server_executor = init_server_executor()
    execution_engine = init_execution_engine()
    
    # Wire together
    execution_engine.set_server_executor(server_executor)
    logger.info("✅ All components initialized\n")
    
    # Step 3: Generate task plan (simulate LLM)
    logger.info("Step 3: Generating task plan...")
    user_id = "test_user_123"
    
    tasks = [
        Task(
            task_id="search_gold",
            tool="web_search",
            execution_target="server",
            depends_on=[],
            inputs={
                "query": "today gold price USD",
                "max_results": 5
            },
            lifecycle_messages={
                "on_start": "🔍 Searching for gold prices...",
                "on_success": "✅ Found gold price data!",
                "on_failure": "❌ Search failed"
            },
            control={
                "timeout_ms": 5000
            }
        ),
        Task(
            task_id="search_news",
            tool="web_search",
            execution_target="server",
            depends_on=[],
            inputs={
                "query": "latest tech news",
                "max_results": 3
            },
            lifecycle_messages={
                "on_start": "📰 Searching for news...",
                "on_success": "✅ Found latest news!",
                "on_failure": "❌ News search failed"
            }
        )
    ]
    
    logger.info(f"✅ Generated {len(tasks)} tasks\n")
    
    # Step 4: Register tasks
    logger.info("Step 4: Registering tasks with orchestrator...")
    await orchestrator.register_tasks(user_id, tasks)
    logger.info("✅ Tasks registered\n")
    
    # Step 5: Start execution (NON-BLOCKING!)
    logger.info("Step 5: Starting execution engine...")
    await execution_engine.start_execution(user_id)
    logger.info("✅ Execution started in background!\n")
    
    logger.info("="*70)
    logger.info("WATCHING EXECUTION (engine runs automatically)")
    logger.info("="*70 + "\n")
    
    # Step 6: Wait for completion
    # Engine runs in background, we just wait here
    await asyncio.sleep(3)  # Give it time to execute
    
    # Check final status
    logger.info("\n" + "="*70)
    logger.info("CHECKING FINAL STATUS")
    logger.info("="*70 + "\n")
    
    summary = await orchestrator.get_execution_summary(user_id)
    logger.info(f"Total: {summary['total']}")
    logger.info(f"Completed: {summary['completed']}")
    logger.info(f"Failed: {summary['failed']}")
    logger.info(f"Pending: {summary['pending']}")
    
    # Show task outputs
    state = orchestrator.get_state(user_id)
    if state:
        logger.info("\nTask Outputs:")
        for task_id, record in state.tasks.items():
            if record.output:
                logger.info(f"\n{task_id}:")
                logger.info(f"  Status: {record.status}")
                logger.info(f"  Duration: {record.duration_ms}ms")
                logger.info(f"  Message: {record.output}")
                if record.output.success:
                    logger.info(f"  Data: {list(record.output.data.keys())}")
    
    logger.info("\n" + "="*70)
    logger.info("TEST COMPLETE!")
    logger.info("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())