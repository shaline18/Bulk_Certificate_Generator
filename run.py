"""Start the Certify backend and open the app in your browser.

Run:  uv run python run.py
"""
import threading
import time
import webbrowser

import uvicorn

APP_URL = "http://127.0.0.1:8000/app/"


def open_browser():
    time.sleep(2)  # give the server a moment to start
    webbrowser.open(APP_URL)


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(
        "bulk_certificate_generator.main:app",
        app_dir="src",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
