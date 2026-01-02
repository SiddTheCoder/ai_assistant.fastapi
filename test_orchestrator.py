"""
Test showing OLD vs NEW orchestrator behavior
"""

import asyncio
from app.core.orchestrator import TaskOrchestrator
from app.registry.loader import get_tool_registry
from app.core.models import Task, ExecutionState

# ========================================
# TEST CASE: C→C→C Chain
# ========================================

async def test_client_chain():
    """
    Test: create_folder → write_file → copy_file
    All client tasks, chained dependencies
    """
    
    print("="*70)
    print("TEST: Client Chain (C→C→C)")
    orchestrator = TaskOrchestrator()
    user_id = "test_user"
    
    # Create tasks
    tasks = [
        Task(
            task_id="create_folder",
            tool="folder_create",
            execution_target="client",
            depends_on=[],
            inputs={"path": "~/test"}
        ),
         Task(
            task_id="search",
            tool="web_search",
            execution_target="server",
            depends_on=[],
            inputs={"query": "test"}
        ),
        Task(
            task_id="write_file",
            tool="file_create",
            execution_target="client",
            depends_on=["create_folder", "search"],
            inputs={"path": "~/test/file.txt"}
        ),
        Task(
            task_id="copy_file",
            tool="file_copy",
            execution_target="client",
            depends_on=["write_file"],
            inputs={"source": "~/test/file.txt", "dest": "~/backup/file.txt"}
        )
    ]
    
    # Register
    await orchestrator.register_tasks(user_id, tasks)

    states = orchestrator.states[user_id]
    # print("states", states)
    
    # ✅ NEW BEHAVIOR: Get batch
    print("\n📦 Getting executable batch...")
    batch = await orchestrator.get_executable_batch(user_id)
    
    print(f"\nServer tasks: {len(batch.server_tasks)}")
    # print(f"\nServer tasks: {batch.server_tasks}")
    print(f"Client tasks: {len(batch.client_tasks)}")
    print({t.task_id for t in batch.client_tasks})
    # print(f"\nServer tasks: {batch.client_tasks}")
    # if batch.client_tasks:
    #     print(f"\n✅ Client tasks returned:")
    #     for task in batch.client_tasks:
    #         deps = f" (depends: {task.depends_on})" if task.depends_on else ""
    #         print(f"   - {task.task_id}{deps}")
    
    print("\n" + "="*70)
    
    # Expected:
    # Client tasks: 3  ← ALL THREE AT ONCE!
    # - create_folder
    # - write_file (depends: ['create_folder'])
    # - copy_file (depends: ['write_file'])


# ========================================
# TEST CASE: S→C→C (Mixed)
# ========================================

async def test_mixed_chain():
    """
    Test: web_search (S) → web_search (S) → create_folder (C) → write_file (C)
    Mixed server/client chain with proper iteration flow
    """
    
    print("\n" + "="*70)
    print("TEST: Mixed Chain (S→S→C→C)")
    print("="*70)
    
    orchestrator = TaskOrchestrator()
    user_id = "test_user2"
    
    tasks = [
        Task(
            task_id="search0",
            tool="web_search",
            execution_target="server",
            depends_on=[],
            inputs={"query": "test0"}
        ),
        Task(
            task_id="search1",
            tool="web_search",
            execution_target="server",
            depends_on=["search0"],
            inputs={"query": "test1"}
        ),
        Task(
            task_id="create_folder",
            tool="folder_create",
            execution_target="client",
            depends_on=["search1"],
            inputs={"path": "~/results"}
        ),
        Task(
            task_id="write_file",
            tool="file_create",
            execution_target="client",
            depends_on=["create_folder"],
            inputs={"path": "~/results/data.txt"}
        )
    ]
    
    await orchestrator.register_tasks(user_id, tasks)
    
    # Iteration 1: Only search0 runnable
    print("\n📦 Iteration 1: Getting executable batch...")
    batch = await orchestrator.get_executable_batch(user_id)
    print(f"Server tasks: {[t.task_id for t in batch.server_tasks]}")
    print(f"Client tasks: {[t.task_id for t in batch.client_tasks]}")
    print("Expected: Server=['search0'], Client=[]")
    
    # Simulate search0 completion
    from app.core.models import TaskOutput
    print("\n✅ Completing search0...")
    await orchestrator.mark_task_completed(
        user_id, 
        "search0",
        TaskOutput(success=True, data={"results": "search0 data"})
    )
    
    # Iteration 2: Now search1 runnable
    print("\n📦 Iteration 2: Getting executable batch...")
    batch = await orchestrator.get_executable_batch(user_id)
    print(f"Server tasks: {[t.task_id for t in batch.server_tasks]}")
    print(f"Client tasks: {[t.task_id for t in batch.client_tasks]}")
    print("Expected: Server=['search1'], Client=[]")
    
    # Simulate search1 completion
    print("\n✅ Completing search1...")
    await orchestrator.mark_task_completed(
        user_id, 
        "search1",
        TaskOutput(success=True, data={"results": "search1 data"})
    )
    
    # Iteration 3: Client chain becomes runnable!
    print("\n📦 Iteration 3: Getting executable batch...")
    batch = await orchestrator.get_executable_batch(user_id)
    print(f"Server tasks: {[t.task_id for t in batch.server_tasks]}")
    print(f"Client tasks: {[t.task_id for t in batch.client_tasks]}")
    print("Expected: Server=[], Client=['create_folder', 'write_file'] ← CHAIN!")
    
    if batch.client_tasks:
        print(f"\n✅ Client tasks returned (detected chain):")
        for task in batch.client_tasks:
            deps = f" (depends: {task.depends_on})" if task.depends_on else ""
            print(f"   - {task.task_id}{deps}")
    
    print("\n" + "="*70) 
    
async def test_independent_clients():
    """
    Test: open_chrome, open_vscode, open_spotify
    Independent client tasks
    """
    
    print("\n" + "="*70)
    print("TEST: Independent Clients")
    print("="*70)
    
    orchestrator = TaskOrchestrator()
    user_id = "test_user3"
    
    tasks = [
        Task(
            task_id="open_chrome",
            tool="open_app",
            execution_target="client",
            depends_on=[],
            inputs={"target": "chrome"}
        ),
        Task(
            task_id="open_vscode",
            tool="open_app",
            execution_target="client",
            depends_on=[],
            inputs={"target": "vscode"}
        ),
        Task(
            task_id="open_spotify",
            tool="open_app",
            execution_target="client",
            depends_on=[],
            inputs={"target": "spotify"}
        )
    ]
    
    await orchestrator.register_tasks(user_id, tasks)
    
    print("\n📦 Getting executable batch...")
    batch = await orchestrator.get_executable_batch(user_id)
    print(f"Client tasks: {[t.task_id for t in batch.client_tasks]}")
    
    print("\n✅ All independent tasks returned together")
    print("   Client can execute them in parallel!")
    
    print("\n" + "="*70)
    
    # Expected:
    # Client tasks: ['open_chrome', 'open_vscode', 'open_spotify']
    # All returned at once (no chains, just all runnable)



async def main():
    get_tool_registry().load()
    
    # await test_client_chain()
    await test_mixed_chain()
    # await test_independent_clients()


if __name__ == "__main__":
    asyncio.run(main())