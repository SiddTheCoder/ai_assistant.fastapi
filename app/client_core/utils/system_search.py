"""
Cross-platform system search utility.
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


# Common aliases for cross-platform support
APP_ALIASES = {
    # Text Editors
    "code": {
        "win32": ["code", "Visual Studio Code"],
        "darwin": ["Visual Studio Code"],
        "linux": ["code", "visual-studio-code"]
    },
    "vscode": {
        "win32": ["code", "Visual Studio Code"],
        "darwin": ["Visual Studio Code"],
        "linux": ["code", "visual-studio-code"]
    },
    "sublime": {
        "win32": ["sublime_text", "Sublime Text"],
        "darwin": ["Sublime Text"],
        "linux": ["subl", "sublime_text"]
    },
    "notepad": {
        "win32": ["notepad", "notepad.exe"],
        "darwin": ["TextEdit"],
        "linux": ["gedit", "kate", "xed", "mousepad", "leafpad"]
    },
    "textedit": {
        "win32": ["notepad"],
        "darwin": ["TextEdit"],
        "linux": ["gedit"]
    },
    
    # Terminals
    "terminal": {
        "win32": ["cmd.exe", "powershell.exe", "wt.exe"],
        "darwin": ["Terminal", "iTerm"],
        "linux": ["gnome-terminal", "konsole", "xterm", "tilix"]
    },
    
    # Browsers
    "chrome": {
        "win32": ["chrome.exe", "Google Chrome.lnk"],
        "darwin": ["Google Chrome"],
        "linux": ["google-chrome", "chromium"]
    },
    "firefox": {
        "win32": ["firefox.exe", "Mozilla Firefox.lnk"],
        "darwin": ["Firefox"],
        "linux": ["firefox"]
    },
    "zen": {
        "win32": ["Zen.exe", "Zen Firefox.lnk"],
        "darwin": ["Zen"],
        "linux": ["Zen"]
    },
    
    # File Managers
    "finder": {
        "win32": ["explorer.exe"],
        "darwin": ["Finder"],
        "linux": ["nautilus", "dolphin", "thunar"]
    },
    "explorer": {
        "win32": ["explorer.exe"],
        "darwin": ["Finder"],
        "linux": ["nautilus"]
    },
    
    # Media
    "camera": {
        "win32": ["microsoft.windows.camera:"],
        "darwin": ["Photo Booth"],
        "linux": ["cheese", "gnome-camera"]
    },
    
    # Utilities
    "calc": {
        "win32": ["calc.exe"],
        "darwin": ["Calculator"],
        "linux": ["gnome-calculator", "kcalc"]
    },
    "calculator": {
        "win32": ["calc.exe"],
        "darwin": ["Calculator"],
        "linux": ["gnome-calculator", "kcalc"]
    }
}

class SystemSearcher:
    """
    Helper class to search for applications and files across different OSs.
    """
    
    def __init__(self):
        self.os_type = sys.platform
        self.logger = logging.getLogger("client.utils.SystemSearcher")

    def find_app(self, app_name: str) -> Optional[str]:
        """
        Find an application's executable path or launchable file.
        Handles cross-platform aliases (e.g. 'notepad' -> 'TextEdit' on Mac).
        
        Args:
            app_name: Name of the application (e.g., "chrome", "code", "notepad")
            
        Returns:
            Path to the application or None if not found.
        """
        self.logger.info(f"Searching for app: {app_name} on {self.os_type}")
        
        # 1. Check Aliases First
        search_candidates = [app_name]
        
        app_name_lower = app_name.lower()
        if app_name_lower in APP_ALIASES:
            # Get list of possible names for this OS
            aliases = APP_ALIASES[app_name_lower].get(self.os_type)
            if not aliases and self.os_type.startswith("linux"):
                 aliases = APP_ALIASES[app_name_lower].get("linux")
                 
            if aliases:
                self.logger.info(f"Resolving alias '{app_name}' -> {aliases}")
                # Special handling for UWP protocols (Windows)
                if self.os_type == "win32":
                    for alias in aliases:
                        if alias.endswith(":"):
                            return alias
                            
                search_candidates = aliases + [app_name] # Try aliases first, then original
        
        # 2. Iterate through candidates
        for candidate in search_candidates:
            # A. Exact match in PATH (fastest)
            path = shutil.which(candidate)
            if path:
                return path
                
            # B. OS-specific deep search
            found_path = None
            if self.os_type == "win32":
                found_path = self._find_app_windows(candidate)
            elif self.os_type == "darwin":
                found_path = self._find_app_mac(candidate)
            elif self.os_type.startswith("linux"):
                found_path = self._find_app_linux(candidate)
            
            if found_path:
                return found_path
                
        return None

    def _find_app_windows(self, app_name: str) -> Optional[str]:
        """
        Search for Windows apps in Start Menu shortcuts and common paths.
        """
        # Common locations for Start Menu shortcuts
        locations = [
            os.path.join(os.environ["PROGRAMDATA"], "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")
        ]
        
        app_name_lower = app_name.lower()
        
        # Search for .lnk files (Shortcuts) - BEST for user apps
        for location in locations:
            if not os.path.exists(location):
                continue
                
            for root, _, files in os.walk(location):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        name_no_ext = file.lower().replace(".lnk", "")
                        
                        # 1. Exact/Substring match
                        if app_name_lower == name_no_ext or app_name_lower in name_no_ext:
                             return os.path.join(root, file)
                             
                        # 2. "Acronym" / Fuzzy match (e.g. vscode -> Visual Studio Code)
                        # Check if all chars in app_name appear in name_no_ext in order
                        # but only if query is at least 3 chars to avoid false positives
                        if len(app_name_lower) >= 3 and self._fuzzy_match(app_name_lower, name_no_ext):
                            return os.path.join(root, file)

        return None

    def _fuzzy_match(self, query: str, text: str) -> bool:
        """
        Simple fuzzy match: checks if characters of query appear in text in order.
        Example: 'vscode' matches 'visual studio code'
        """
        q_idx = 0
        t_idx = 0
        while q_idx < len(query) and t_idx < len(text):
            if query[q_idx] == text[t_idx]:
                q_idx += 1
            t_idx += 1
        return q_idx == len(query)

    def _find_app_mac(self, app_name: str) -> Optional[str]:
        """
        Search for macOS apps using mdfind (Spotlight) or standard paths.
        """
        # 1. Use mdfind (Spotlight) - Extremely fast and accurate
        try:
            # kMDItemContentTypeTree=com.apple.application-bundle
            cmd = ["mdfind", f"kMDItemContentTypeTree=com.apple.application-bundle && kMDItemFSName == '*{app_name}*'"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                # Return first match
                return result.stdout.strip().split('\n')[0]
        except Exception as e:
            self.logger.warning(f"mdfind failed: {e}")

        # 2. Fallback: Manual search in /Applications
        search_paths = ["/Applications", "/System/Applications", os.path.expanduser("~/Applications")]
        app_name_lower = app_name.lower()
        
        for path in search_paths:
            if not os.path.exists(path):
                continue
            for item in os.listdir(path):
                if item.lower().endswith(".app") and app_name_lower in item.lower():
                    return os.path.join(path, item)
                    
        return None

    def _find_app_linux(self, app_name: str) -> Optional[str]:
        """
        Search for Linux apps in /usr/share/applications (.desktop files) or bin.
        """
        # Search .desktop files
        search_paths = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications")
        ]
        
        app_name_lower = app_name.lower()
        
        for path in search_paths:
            if not os.path.exists(path):
                continue
            for item in os.listdir(path):
                if item.lower().endswith(".desktop") and app_name_lower in item.lower():
                    # We return the .desktop file path. 
                    # Launching it usually requires `gtk-launch` or parsing the `Exec=` line.
                    # For simplicity, returning the .desktop path is a good start, 
                    # but the `OpenAppTool` will need to handle it.
                    return os.path.join(path, item)
                    
        return None
