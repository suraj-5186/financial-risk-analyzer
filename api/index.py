import os
import sys
import shutil

# Add backend and project root directories to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_dir = os.path.join(root_dir, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Initialize /tmp database if running on Vercel
if os.getenv("VERCEL"):
    tmp_db = "/tmp/financial_risk.db"
    orig_db = os.path.join(backend_dir, "financial_risk.db")
    if not os.path.exists(tmp_db) and os.path.exists(orig_db):
        try:
            shutil.copyfile(orig_db, tmp_db)
        except Exception as e:
            print(f"Error copying DB to /tmp: {e}")

from main import app
