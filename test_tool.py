# ✅ NEW: Import orchestration system
from app.registry.loader import load_tool_registry, get_tool_registry
from app.core.orchestrator import init_orchestrator, get_orchestrator

import logging
logger = logging.getLogger(__name__)


async def main ():
  # ✅ NEW: Initialize Orchestrator
#   print("\n🎯 Initializing Task Orchestrator...")
#   try:
#         orchestrator = init_orchestrator()
#         print("✅ Task Orchestrator initialized", orchestrator)
#         await orchestrator.register_tasks("user1", [])
#         await orchestrator.register_tasks("user2", [])
#         await orchestrator.register_tasks("user3", [])
#         await orchestrator.register_tasks("user4", [])
#         await orchestrator.register_tasks("user5", [])
#         print("📦 State:",orchestrator.states)
#   except Exception as e:
#         print(f"❌ Failed to initialize orchestrator: {e}")
#         raise
  logger.info("\n📦 Loading Tool Registry...")
  try:
        load_tool_registry()
        registry = get_tool_registry()
        print("registry", registry)
      #   registry.print_summary()
  except Exception as e:
        print(f"❌ Failed to load tool registry: {e}")
        raise
    
  
import asyncio
asyncio.run(main())  