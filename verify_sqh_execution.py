
import asyncio
import json
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.models import Task
from app.core.orchestrator import get_orchestrator
from app.core.execution_engine import get_execution_engine
from app.core.server_executor import get_server_executor
from app.core.task_emitter import get_task_emitter
from app.registry.loader import load_tool_registry, get_tool_registry

# Mock raw response from user log
RAW_JSON = """{
  "tasks": [
    {
      "task_id": "step_1",
      "tool": "open_app",
      "execution_target": "client",
      "depends_on": [],
      "inputs": {
        "target": "vscode"
      },
      "lifecycle_messages": {
        "on_start": "Opening VS Code for you, Sir...",
        "on_success": "VS Code is open, Sir.",
        "on_failure": "Failed to open VS Code, Sir."
      },
      "control": {
        "on_failure": "abort"
      }
    },
    {
      "task_id": "step_2",
      "tool": "file_create",
      "execution_target": "client",
      "depends_on": [],
      "inputs": {
        "path": "AI_Note.txt",
        "content": "Artificial Intelligence (AI) content"
      },
      "lifecycle_messages": {
        "on_start": "Creating an AI-related note, Sir...",
        "on_success": "AI note created successfully, Sir.",
        "on_failure": "Failed to create the AI note, Sir."
      },
      "control": {
        "on_failure": "abort"
      }
    },
    {
      "task_id": "step_3",
      "tool": "file_open",
      "execution_target": "client",
      "depends_on": [ "step_2" ],
      "input_bindings": {
        "path": "$.tasks.step_2.output.data.file_path"
      },
      "inputs": {
        "app": "notepad"
      },
       "lifecycle_messages": {
        "on_start": "Opening the AI note in Notepad, Sir...",
        "on_success": "AI note opened in Notepad, Sir.",
        "on_failure": "Couldn't open the AI note in Notepad, Sir."
      },
      "control": {
        "on_failure": "abort"
      }
    }
  ]
}"""

async def simulate_sqh_process():
    user_id = "debug_user"
    
    # Ensure registries are loaded for validation 
    # (Since Task model creation might imply checking valid fields? No, Pydantic strict mode is on types not registry content yet)
    # But ExecutionEngine needs registry
    get_tool_registry()

    print(f"\n🚀 Simulating SQH Process for {user_id}")
    
    try:
        # 1. Parse Response
        print("1. Parsing JSON...")
        data = json.loads(RAW_JSON)
        tasks_data = data.get("tasks", [])
        tasks = []
        for i, task_data in enumerate(tasks_data):
            try:
                print(f"   Parsing task {i+1}: {task_data.get('tool')}")
                t = Task(**task_data)
                tasks.append(t)
            except Exception as e:
                print(f"   ❌ Failed to parse task {i+1}: {e}")
                
        print(f"✅ Parsed {len(tasks)} tasks")
        
        # 2. Register Tasks
        print("2. Registering Tasks...")
        orchestrator = get_orchestrator()
        await orchestrator.register_tasks(user_id, tasks)
        print("✅ Tasks registered")
        
        # DEBUG: Check state
        state = orchestrator.get_state(user_id)
        with open("verify_output.txt", "w", encoding="utf-8") as f:
            if state:
                f.write(f"State Tasks: {len(state.tasks)}\n")
                for tid, t in state.tasks.items():
                    f.write(f"Task: {tid}\n")
                    f.write(f"  Tool: {t.tool}\n")
                    f.write(f"  Status: {t.status}\n")
                    f.write(f"  Error: {t.error}\n")
                    f.write(f"  Deps: {t.depends_on}\n")
                    f.write("-" * 20 + "\n")
            else:
                f.write("❌ No state found for user!\n")

        # 3. Trigger Execution
        print("3. Triggering Execution Engine...")
        execution_engine = get_execution_engine()
        
        # Inject dependencies (Using Real Singleton Emitter)
        # Note: We configure it with a callback to see output in this script
        emitter = get_task_emitter()
        
        async def script_callback(uid, task_batch):
            with open("verify_output.txt", "a", encoding="utf-8") as f:
                f.write(f"\n[CLIENT EMITTER] -> User {uid} received batch:\n")
                for t in task_batch:
                    f.write(f"   >> Task: {t.get('task_id')} | Tool: {t.get('tool')}\n")
                
        emitter.set_client_callback(script_callback)
        execution_engine.set_client_emitter(emitter)
        
        # Inject Server Executor (Real)
        execution_engine.set_server_executor(get_server_executor())

        print("   Starting Execution...")
        task = await execution_engine.start_execution(user_id)
        
        # Wait for meaningful amount of time to let execution loop run
        # Loop interval is ~0.5s in execution_engine code
        print("   Waiting for execution loop...")
        await asyncio.sleep(3)
        
        # Check status
        summary = await orchestrator.get_execution_summary(user_id)
        with open("verify_output.txt", "a", encoding="utf-8") as f:
             f.write(f"\n📊 Execution Summary: {summary}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simulate_sqh_process())
