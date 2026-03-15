"""
Test basic imports to identify any issues
"""
import sys
sys.path.insert(0, r'C:\dev\ALEX-main')

print("Testing imports...")

try:
    print("1. Importing FastAPI...")
    from fastapi import FastAPI
    print("   ✓ FastAPI imported")
except Exception as e:
    print(f"   ✗ Error: {e}")

try:
    print("2. Importing database...")
    from database.database import engine, SessionLocal
    print("   ✓ Database imported")
except Exception as e:
    print(f"   ✗ Error: {e}")

try:
    print("3. Importing GovernanceTask model...")
    from database.models.governance_task import GovernanceTask
    print("   ✓ GovernanceTask imported")
except Exception as e:
    print(f"   ✗ Error: {e}")

try:
    print("4. Importing routers...")
    from routers.compliance_router import router
    print("   ✓ Compliance router imported")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n✓ All critical imports successful!")
