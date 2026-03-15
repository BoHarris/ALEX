"""
Test that the queries that were failing now work correctly
"""
import sys
sys.path.insert(0, r'C:\dev\ALEX-main')

from database.database import SessionLocal
from database.models.governance_task import GovernanceTask

print("Testing the previously failing query...")
print("=" * 60)

try:
    db = SessionLocal()
    
    # This is the query that was failing
    print("Executing: db.query(GovernanceTask).filter(GovernanceTask.company_id == 1).all()")
    tasks = db.query(GovernanceTask).filter(GovernanceTask.company_id == 1).all()
    
    print(f"✓ Query succeeded!")
    print(f"  Found {len(tasks)} tasks")
    
    if len(tasks) > 0:
        print(f"\n  Sample task:")
        task = tasks[0]
        print(f"    ID: {task.id}")
        print(f"    Title: {task.title}")
        print(f"    Status: {task.status}")
        print(f"    linked_source_id: {task.linked_source_id}")
        print(f"    linked_source_metadata: {task.linked_source_metadata}")
    
    db.close()
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - Schema fix is working correctly!")
    print("=" * 60)
    
except Exception as e:
    print(f"✗ Query failed with error:")
    print(f"  {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
