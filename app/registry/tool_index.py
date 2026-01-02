from functools import lru_cache
import json
from pathlib import Path

@lru_cache
def get_tools_index(registry_path: str = "registry/tool_index.json"):
    path = Path("app") / registry_path

    if not path.exists():
        raise FileNotFoundError(f"Tool index not found at {path}")

    with open(path, "r") as f:
        return json.load(f).get("tools", [])