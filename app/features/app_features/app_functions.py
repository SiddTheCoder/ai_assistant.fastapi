import os
import webbrowser
import subprocess
import sys
import time
import pyautogui
import logging

logger = logging.getLogger(__name__)

# ---------------- Open Notepad function ----------------
def open_notepad(details):
  logger.info(f"Opening Notepad...{details}")
  content = details.get("content", "")

  if sys.platform.startswith("win"):
      subprocess.Popen(["notepad"])
      # Wait a bit for the window to open before typing
      time.sleep(1.2)
      if content:
          pyautogui.typewrite(content, interval=0.05)
  else:
      subprocess.Popen(["gedit"])
      time.sleep(1.5)
      if content:
          pyautogui.typewrite(content, interval=0.05)


# ---------------- Open App function ----------------