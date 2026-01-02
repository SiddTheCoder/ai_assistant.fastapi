# app/registry/loader.py
"""
Tool Registry Loader - Singleton Pattern
Loads tool_registry.json at startup and provides global access
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)
 
def load(registry_path: str = "registry/tool_index.json"):
    
    path = Path()
    print("path", path)
    path = Path("app",registry_path)
    print("path", path)
    
    if not path.exists():
        raise Warning(f"Tool registry not found at {registry_path}")
    
    with open(path, "r") as f:
        data = json.load(f)
    
    print(json.dumps(data.get("tools"), indent=4))

load()