import subprocess
import sys

subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
print("Database migrated to head revision.")
