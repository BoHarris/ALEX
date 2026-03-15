"""
Verify that the schema fix was successful
"""
import sys
sys.path.insert(0, r'C:\dev\ALEX-main')

from database.database import engine
from sqlalchemy import text, MetaData, Table

# Method 1: Using pragma table_info
with engine.connect() as conn:
    result = conn.execute(text("""
        PRAGMA table_info(governance_tasks)
    """))
    
    print("=" * 60)
    print("GOVERNANCE_TASKS TABLE COLUMNS:")
    print("=" * 60)
    for row in result.fetchall():
        col_id, col_name, col_type, not_null, default, pk = row
        print(f"  {col_name:.<40} {col_type}")
    
    # Check specific columns
    conn.execute(text("PRAGMA table_info(governance_tasks)"))
    columns = {row[1] for row in conn.execute(text("PRAGMA table_info(governance_tasks)")).fetchall()}
    
    print("\n" + "=" * 60)
    print("VERIFICATION:")
    print("=" * 60)
    required = ['linked_source_id', 'linked_source_metadata']
    for col in required:
        status = "✓" if col in columns else "✗"
        print(f"  {status} {col}")
