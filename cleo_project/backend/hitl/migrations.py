"""
Database migration script for HITL tables
Run this to create the HITL tables in your database
"""
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

from .models import Base

load_dotenv()


def create_hitl_tables():
    """Create all HITL tables"""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./cleo_data.db')
    engine = create_engine(database_url, echo=True)
    
    print(f"Creating HITL tables in database: {database_url}")
    Base.metadata.create_all(engine)
    print("HITL tables created successfully!")
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    hitl_tables = [t for t in tables if t.startswith('hitl_') or t == 'operators']
    print(f"Created tables: {', '.join(hitl_tables)}")


if __name__ == "__main__":
    create_hitl_tables()
