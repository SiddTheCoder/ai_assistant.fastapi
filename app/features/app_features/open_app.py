import os
import sys
import time
import subprocess
import webbrowser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from app.features.app_features.app_functions import open_notepad

def open_app(details):
    """
    Opens apps or websites normally, or runs Chrome headless search using Selenium
    if 'query' is provided
    """
    command = details.actionDetails.app_name.lower().strip()
    query = getattr(details.actionDetails, "query", "").strip()

    # --- Common app mappings ---
    apps = {
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
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "facebook": "https://facebook.com",
        "chatgpt": "https://chat.openai.com",
        "chess": "https://chess.com",
    }

    # --- Website handling ---
    for name, url in websites.items():
          # --- Chrome logic ---
        if "chrome" in command:
            if query:
                print(f"🔍 Running headless search for '{query}' ...")
                results = fetch_google_results_with_selenium(query)
                details.actionDetails.searchResults = results
                print("✅ Results fetched and appended to actionDetails.")
            else:
                print("🚀 Launching Chrome ...")
                _open_exe("chrome")
            return
        if name in command:
            print(f"🌐 Opening {url} ...")
            webbrowser.open(url)
            return


    # --- Default app logic ---
    for name, exe in apps.items():
        if name in command:
            print(f"🚀 Launching {name} ...")
            try:
                if callable(exe):
                    exe(details)
                else:
                    _open_exe(exe)
            except Exception as e:
                print(f"⚠️ Could not open {name}: {e}")
            return

    print("❌ Sorry, I couldn’t find a match for that command.")

def _open_exe(exe):
    """Cross-platform safe app launcher."""
    if sys.platform.startswith("win"):
        os.system(f"start {exe}")
    elif sys.platform.startswith("darwin"):
        subprocess.Popen(["open", "-a", exe])
    else:
        subprocess.Popen([exe])

def fetch_google_results_with_selenium(query, limit=5):
    """
    Use Selenium to fetch live Google search results underground (headless).
    """
    options = Options()
    options.add_argument("--headless")  # runs Chrome without UI
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    driver.get(search_url)
    driver.get(search_url)
    time.sleep(2)

    results = []
    items = driver.find_elements(By.CSS_SELECTOR, "div.tF2Cxc")[:limit]
    for item in items:
        try:
            title = item.find_element(By.TAG_NAME, "h3").text
            url = item.find_element(By.TAG_NAME, "a").get_attribute("href")
            snippet = item.find_element(By.CSS_SELECTOR, ".VwiC3b").text
            results.append({"title": title, "url": url, "snippet": snippet})
        except Exception:
            continue

    driver.quit()
    return results
