"""
System control tools (Open/Close App).
"""

import os
import sys
import subprocess
import logging
from typing import Dict, Any

from ..base import BaseTool, ToolOutput
from ...utils.system_search import SystemSearcher

class OpenAppTool(BaseTool):
    """Open application tool."""
    
    def get_tool_name(self) -> str:
        return "open_app"
    
    def __init__(self):
        super().__init__()
        self.searcher = SystemSearcher()
    
    async def _execute(self, inputs: Dict[str, Any]) -> ToolOutput:
        """Find and open an application."""
        from datetime import datetime
        
        target = inputs.get("target", "")
        args = inputs.get("args", [])
        
        if not target:
            return ToolOutput(success=False, data={}, error="Target app name is required")
            
        try:
            # 1. Find the app
            app_path = self.searcher.find_app(target)
            
            if not app_path:
                return ToolOutput(
                    success=False, 
                    data={}, 
                    error=f"Application '{target}' not found in your system boss"
                )
                
            self.logger.info(f"Opening app at: {app_path}")
            
            # 2. Launch it based on OS
            process_id = 0
            
            if sys.platform == "win32":
                # Windows
                # If args are provided and it's an executable (not lnk/protocol), use subprocess
                if args and not app_path.endswith(".lnk") and not app_path.endswith(":"):
                    cmd = [app_path] + args
                    # Popen doesn't block
                    subprocess.Popen(cmd)
                else:
                     # os.startfile is best for .lnk and protocols
                     os.startfile(app_path)
                     
                process_id = 0 
            elif sys.platform == "darwin":
                cmd = ["open", app_path]
                if args:
                    cmd.extend(["--args"] + args)
                # Use Popen to not block
                subprocess.Popen(cmd)
            else:
                if app_path.endswith(".desktop"):
                    cmd = ["gtk-launch", os.path.basename(app_path).replace(".desktop", "")]
                    subprocess.Popen(cmd)
                else:
                    cmd = [app_path] + args
                    subprocess.Popen(cmd)
            
            return ToolOutput(
                success=True,
                data={
                    "target": target,
                    "path": app_path,
                    "process_id": process_id,
                    "launch_time": datetime.now().isoformat(),
                    "status": "launched"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to open app: {e}")
            return ToolOutput(success=False, data={}, error=str(e))


class CloseAppTool(BaseTool):
    """Close application tool."""
    
    def get_tool_name(self) -> str:
        return "close_app"
    
    async def _execute(self, inputs: Dict[str, Any]) -> ToolOutput:
        """Close/Kill an application."""
        from datetime import datetime
        
        target = inputs.get("target", "")
        force = inputs.get("force", False)
        
        if not target:
            return ToolOutput(success=False, data={}, error="Target app name is required")
            
        try:
            cmd = []
            
            if sys.platform == "win32":
                process_name = target if target.endswith(".exe") else f"{target}.exe"
                cmd = ["taskkill", "/IM", process_name]
                if force:
                    cmd.append("/F")
            else:
                cmd = ["pkill", "-f", target]
                if force:
                    cmd.append("-9")
            
            self.logger.info(f"Closing app with command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return ToolOutput(
                    success=True,
                    data={
                        "target": target,
                        "status": "closed",
                        "exit_code": result.returncode,
                        "closed_at": datetime.now().isoformat(),
                        "output": result.stdout
                    }
                )
            elif result.returncode == 128 or "not found" in result.stderr.lower() or result.returncode == 1:
                # 128 is common exit for pkill if not found, 1 is common for taskkill
                # Process not found
                return ToolOutput(
                    success=False,
                    data={},
                    error=f"Process '{target}' not found or not running"
                )
            else:
                return ToolOutput(
                    success=False, 
                    data={"stderr": result.stderr}, 
                    error=f"Failed to close app ({result.returncode}): {result.stderr}"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to close app: {e}")
            return ToolOutput(success=False, data={}, error=str(e))
