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

"""
Updated OpenAppTool with full Windows Store app support.
"""

import os
import sys
import subprocess
import logging
from typing import Dict, Any
from datetime import datetime


class OpenAppTool(BaseTool):
    """Open application tool with support for all app types."""
    
    def get_tool_name(self) -> str:
        return "open_app"
    
    def __init__(self):
        super().__init__()
        self.searcher = SystemSearcher()
    
    async def _execute(self, inputs: Dict[str, Any]) -> ToolOutput:
        """Find and open an application."""
        target = inputs.get("target", "")
        print("OPEN APP TOOL TARGET:", target)
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
            
            # 2. Launch it based on OS and app type
            process_id = 0
            
            if sys.platform == "win32":
                process_id = self._launch_windows_app(app_path, args)
            elif sys.platform == "darwin":
                self._launch_macos_app(app_path, args)
            else:
                self._launch_linux_app(app_path, args)
            
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
    
    def _launch_windows_app(self, app_path: str, args: list) -> int:
        """
        Launch Windows app - handles Store apps, .lnk, .exe, protocols.
        """
        # 1. Windows Store apps (UWP/MSIX) - WhatsApp, Spotify, etc.
        if app_path.startswith("shell:AppsFolder\\"):
            self.logger.info("Launching Windows Store app via explorer")
            subprocess.Popen(["explorer.exe", app_path])
            return 0
        
        # 2. UWP protocol handlers (e.g., microsoft.windows.camera:)
        if app_path.endswith(":") and not os.path.exists(app_path):
            self.logger.info("Launching UWP protocol")
            os.startfile(app_path)
            return 0
        
        # 3. .lnk shortcuts
        if app_path.endswith(".lnk"):
            self.logger.info("Launching .lnk shortcut")
            os.startfile(app_path)
            return 0
        
        # 4. Regular .exe files
        if app_path.endswith(".exe"):
            if args:
                # With arguments - use subprocess
                self.logger.info(f"Launching .exe with args: {args}")
                cmd = [app_path] + args
                process = subprocess.Popen(cmd)
                return process.pid
            else:
                # No arguments - use os.startfile (better for GUI apps)
                self.logger.info("Launching .exe via startfile")
                os.startfile(app_path)
                return 0
        
        # 5. Fallback - try os.startfile
        self.logger.info("Using fallback os.startfile")
        os.startfile(app_path)
        return 0
    
    def _launch_macos_app(self, app_path: str, args: list):
        """Launch macOS app."""
        cmd = ["open", app_path]
        if args:
            cmd.extend(["--args"] + args)
        subprocess.Popen(cmd)
    
    def _launch_linux_app(self, app_path: str, args: list):
        """Launch Linux app."""
        if app_path.endswith(".desktop"):
            # Use gtk-launch for .desktop files
            cmd = ["gtk-launch", os.path.basename(app_path).replace(".desktop", "")]
            subprocess.Popen(cmd)
        else:
            # Direct executable
            cmd = [app_path] + args
            subprocess.Popen(cmd)

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
