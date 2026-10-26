import sys
from pathlib import Path

# Add project root to sys.path so modules like fallback, models, watchdog are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.app import app

# Vercel serverless function entrypoint
# Exposes 'app' WSGI callable
if __name__ == "__main__":
    app.run()
