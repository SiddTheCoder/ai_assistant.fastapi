import os
import webbrowser
import subprocess
import sys
import time
import pyautogui
from app.features.app_features.app_functions import open_notepad

def open_app(details):
    """
    Open apps or websites based on simple text commands.
    Works on Windows, macOS, and Linux.
    """
    command = details.actionDetails.app_name
    command = command.lower().strip()
   
    # --- Common app mappings ---
    apps = {
        # "name": "exe",
        "chrome": "chrome",
        "vscode": "code",
        "notepad": open_notepad,
        "calculator": "calc" if sys.platform.startswith("win") else "gnome-calculator",
        "spotify": "spotify",
        "whatsapp": "whatsapp",
        "telegram": "telegram",
        "file explorer": "explorer" if sys.platform.startswith("win") else "nautilus",
    }

    # --- Website shortcuts ---
    websites = {
        # "name": "url",
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "facebook": "https://facebook.com",
        "chatgpt": "https://chat.openai.com",
        "chess": "https://chess.com",
    }

    # --- Open website ---
    for name, url in websites.items():
        if name in command:
            print(f"🌐 Opening_web {url} ...")
            webbrowser.open(url)
            return

 # ---------------- App logic ----------------
    for name, exe in apps.items():
        if name in command:
            print(f"🚀 Launching_app {name} ...")
            try:
                if callable(exe):  # ✅ If it's a function, just call it
                    exe(details)
                else:
                    if sys.platform.startswith("win"):
                        os.system(f"start {exe}")
                    elif sys.platform.startswith("darwin"):
                        subprocess.Popen(["open", "-a", exe])
                    else:
                        subprocess.Popen([exe])
            except Exception as e:
                print(f"⚠️ Could not open {name}: {e}")
            return

    print("❌ Sorry, I couldn’t find a match for that command.")
