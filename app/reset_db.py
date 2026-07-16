import sys
from sqlalchemy import create_engine, MetaData
from app.core.config import settings
from app.core.database import Base

# Import all models to ensure they are registered on Base.metadata
from app.models import (
    User,
    UserSession,
    Profile,
    Vital,
    EmergencyContact,
    Allergy,
    MedicalCondition,
    Medication,
    Lifestyle,
    FamilyHistory,
    AdditionalDetail,
    MedicalOption,
)

def reset_database():
    print(f"Connecting to database: {settings.DATABASE_URL}...")
    engine = create_engine(settings.DATABASE_URL)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    print("Dropping all existing tables...")
    # Disable foreign key checks or cascade drop
    from sqlalchemy import text
    with engine.connect() as conn:
        # PostgreSQL cascade drop helper
        for table in metadata.tables.keys():
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
        conn.commit()
    print("All tables dropped successfully.")
    
    print("Creating all tables from updated SQLAlchemy models...")
    Base.metadata.create_all(bind=engine)
    print("Database schema created successfully!")

    print("Registering database schema with Alembic version tracking...")
    with engine.connect() as conn:
        conn.execute(text('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);'))
        conn.execute(text('DELETE FROM alembic_version;'))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('677485fc5d96');"))
        conn.commit()
    print("Alembic version set to head ('677485fc5d96') successfully!")

    print("Seeding default medical options...")
    from app.core.seeding import seed_default_medical_options
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        seed_default_medical_options(db)
        print("Default medical options seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure this is only run in dev environment or with explicit run
    reset_database()

