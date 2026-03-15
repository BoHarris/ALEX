"""
Quick fix to add missing columns to governance_tasks table
"""
import sys
sys.path.insert(0, r'C:\dev\ALEX-main')

from database.database import engine
from sqlalchemy import text

def add_missing_columns():
    """Add missing columns to governance_tasks table if they don't exist"""
    
    with engine.connect() as conn:
        # Check if linked_source_id column exists
        result = conn.execute(text("""
            PRAGMA table_info(governance_tasks)
        """))
        
        existing_columns = {row[1] for row in result.fetchall()}
        print(f"Existing columns: {existing_columns}")
        
        columns_to_add = {
            'linked_source_id': 'INTEGER',
            'linked_source_metadata': 'TEXT'
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    conn.execute(text(f"""
                        ALTER TABLE governance_tasks ADD COLUMN {col_name} {col_type}
                    """))
                    conn.commit()
                    print(f"✓ Added column: {col_name}")
                except Exception as e:
                    print(f"✗ Failed to add {col_name}: {e}")
            else:
                print(f"✓ Column already exists: {col_name}")
        
        # Create indexes for the new columns
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_governance_tasks_linked_source_id 
                ON governance_tasks(linked_source_id)
            """))
            conn.commit()
            print("✓ Created index for linked_source_id")
        except Exception as e:
            print(f"! Index creation note: {e}")

if __name__ == "__main__":
    print("Fixing governance_tasks schema...")
    add_missing_columns()
    print("Schema fix complete!")
