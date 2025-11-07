import os
import webbrowser
import subprocess
import sys
import time
import pyautogui
import logging
from app.utils.fomat_raw_text import format_raw_text

logger = logging.getLogger(__name__)

# ---------------- Open Notepad function ----------------
def open_notepad(details):

  content = details.answerDetails.content
  content = format_raw_text(content)

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