import os
import subprocess
import sys

from database.database import DATABASE_URL, IS_SQLITE_URL

if IS_SQLITE_URL:
    sqlite_path = DATABASE_URL.split("sqlite:///", 1)[1]
    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)

subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
print("Database reset complete and migrated to head revision.")
