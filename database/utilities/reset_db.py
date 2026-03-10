from database.database import Base, engine
from database.models import scan_results, user, company# Import all models

# DANGER: This will drop all tables
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Database reset complete.")