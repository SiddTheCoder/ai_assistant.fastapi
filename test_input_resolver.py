
import logging
from typing import Any, Dict, Optional
from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError
import json

from app.core.models import ExecutionState, TaskRecord

logger = logging.getLogger(__name__)

def main():
  txt = "$.task1.output.data.formatted_results"
  parts = txt[2:].split(".", 1)
  print(parts)
  print(parts[0])
  print(parts[1])
  json_expr = parse(f"$.{parts[1]}")
  print(f"json_expr: {json_expr}")
  search_data = _get_search0_web_result()
  output_data = search_data["output"]["data"]
  print("search_data", json.dumps(output_data, indent=2))
  print(f"json_expr.find('data'): {json_expr.find(search_data)}")


  
def _get_search0_web_result():
    """
    Returns the exact web_search task result payload for:
    query = 'today gold price'
    """

    return {
        "task": {
            "task_id": "search0",
            "tool": "web_search",
            "execution_target": "server",
            "depends_on": [],
            "inputs": {
                "query": "today gold price"
            },
            "input_bindings": {},
            "lifecycle_messages": None,
            "control": None
        },
        "status": "completed",
        "resolved_inputs": {},
        "output": {
            "success": True,
            "data": {
                "results": [
                    {
                        "title": "Gold Price Today in United States | GoldRate",
                        "url": "https://goldrate.com/en/gold/united-states",
                        "snippet": "The price of Gold in United States today is $139.28 per gram for 24k gold."
                    },
                    {
                        "title": "Gold Price Today : Live Updates",
                        "url": "https://skilling.com/eu/en/commodities/gold/",
                        "snippet": "Current Gold Price Trends. In recent months, gold prices today have exhibited a bullish trend."
                    }
                ],
                "total_results": 10,
                "search_time_ms": 4236.66
            },
            "error": None
        },
        "error": None,
        "created_at": "2026-01-03 19:06:28.606494",
        "started_at": "2026-01-03 19:06:28.607521",
        "completed_at": "2026-01-03 19:06:33.353354",
        "duration_ms": 4745,
        "emitted_at": None,
        "ack_received_at": None
    }


main()


