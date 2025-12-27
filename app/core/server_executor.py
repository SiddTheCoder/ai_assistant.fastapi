# app/core/server_executor.py
"""
Server Tool Executor

Executes server-side tools (web_search, api_call, etc.)
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from app.core.models import TaskRecord, TaskOutput
from app.registry.loader import get_tool_registry

logger = logging.getLogger(__name__)


class ServerToolExecutor:
    """
    Executes server-side tools
    
    Tools are registered by name and executed via adapters
    """
    
    def __init__(self):
        self.tool_registry = get_tool_registry()
        self.adapters: Dict[str, Callable] = {}
        
        # Register default adapters
        self._register_default_adapters()
        
        logger.info("✅ Server Tool Executor initialized")
    
    def _register_default_adapters(self):
        """Register built-in tool adapters"""
        self.register_adapter("web_search", self._execute_web_search)
        # More will be added as we implement them
    
    def register_adapter(self, tool_name: str, adapter: Callable):
        """Register a tool adapter"""
        self.adapters[tool_name] = adapter
        logger.info(f"  ✅ Registered adapter: {tool_name}")
    
    async def execute(self, task: TaskRecord) -> TaskOutput:
        """
        Execute a task using the appropriate adapter
        
        Args:
            task: TaskRecord with full task context
            
        Returns:
            TaskOutput with results
        """
        tool_name = task.tool
        
        # Validate tool exists in registry
        if not self.tool_registry.validate_tool(tool_name):
            return TaskOutput(
                success=False,
                data={},
                error=f"Tool '{tool_name}' not found in registry"
            )
        
        # Find adapter
        adapter = self.adapters.get(tool_name)
        if not adapter:
            return TaskOutput(
                success=False,
                data={},
                error=f"No adapter registered for tool '{tool_name}'"
            )
        
        # Get inputs (use resolved_inputs if available, else task.inputs)
        inputs = task.resolved_inputs if task.resolved_inputs else task.task.inputs
        
        try:
            # Execute the adapter
            output = await adapter(inputs)
            return output
        
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return TaskOutput(
                success=False,
                data={},
                error=str(e)
            )
    
    # ========================================
    # TOOL ADAPTERS (Server-side implementations)
    # ========================================
    
    async def _execute_web_search(self, inputs: Dict[str, Any]) -> TaskOutput:
        """
        Execute web_search tool
        
        For now: mock implementation
        Later: integrate actual search API (SerpAPI, Brave, etc.)
        """
        query = inputs.get("query", "")
        max_results = inputs.get("max_results", 10)
        
        logger.info(f"    🔍 Searching: '{query}'")
        
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        # Mock search results
        results = [
            {
                "title": f"Search Result for '{query}' - 1",
                "url": f"https://example.com/search?q={query}",
                "snippet": f"This is a search result about {query}",
                "relevance_score": 0.95
            },
            {
                "title": f"Search Result for '{query}' - 2",
                "url": f"https://example.com/result2",
                "snippet": f"More information about {query}",
                "relevance_score": 0.87
            }
        ]
        
        # Format results nicely
        formatted = self._format_search_results(query, results)
        
        return TaskOutput(
            success=True,
            data={
                "query": query,
                "results": results[:max_results],
                "total_results": len(results),
                "search_time_ms": 500,
                "formatted_results": formatted
            }
        )
    
    def _format_search_results(self, query: str, results: list) -> str:
        """Format search results as readable text"""
        lines = [
            f"Search Results for: '{query}'",
            "=" * 60,
            ""
        ]
        
        for i, result in enumerate(results, 1):
            lines.append(f"{i}. {result['title']}")
            lines.append(f"   URL: {result['url']}")
            lines.append(f"   {result['snippet']}")
            lines.append("")
        
        lines.append(f"Total results: {len(results)}")
        lines.append(f"Searched at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)


# Global singleton
_server_executor: Optional[ServerToolExecutor] = None


def get_server_executor() -> ServerToolExecutor:
    """Get global server executor instance"""
    global _server_executor
    if _server_executor is None:
        _server_executor = ServerToolExecutor()
    return _server_executor


def init_server_executor() -> ServerToolExecutor:
    """Initialize server executor at startup"""
    global _server_executor
    _server_executor = ServerToolExecutor()
    return _server_executor