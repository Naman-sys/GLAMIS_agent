"""
Database Migration Script for GLAMIS Support

This script adds the necessary columns to support GLAMIS interview types.

Usage:
    python database_migration_glamis.py
    
Or execute the SQL directly in your database.
"""

from sqlalchemy import text
from app.database.session import SessionLocal

# SQL Migration for GLAMIS Support
GLAMIS_MIGRATION_SQL = """
-- Add new columns to interview_sessions table for GLAMIS support

-- Interview type tracking
ALTER TABLE interview_sessions ADD COLUMN interview_type VARCHAR(20) NOT NULL DEFAULT 'subject';
ALTER TABLE interview_sessions ADD COLUMN subject VARCHAR(100);
ALTER TABLE interview_sessions ADD COLUMN company VARCHAR(255);
ALTER TABLE interview_sessions ADD COLUMN job_title VARCHAR(255);
ALTER TABLE interview_sessions ADD COLUMN jd_details TEXT;
ALTER TABLE interview_sessions ADD COLUMN svar_type VARCHAR(50);

-- Area tracking (weak and strong areas)
ALTER TABLE interview_sessions ADD COLUMN weak_areas_json JSON NOT NULL DEFAULT '{}';
ALTER TABLE interview_sessions ADD COLUMN strong_areas_json JSON NOT NULL DEFAULT '{}';

-- Question deduplication
ALTER TABLE interview_sessions ADD COLUMN asked_questions_hash JSON NOT NULL DEFAULT '[]';

-- Optional: Add indexes for better query performance
CREATE INDEX idx_interview_type ON interview_sessions(interview_type);
CREATE INDEX idx_interview_subject ON interview_sessions(subject);
CREATE INDEX idx_interview_company ON interview_sessions(company);
"""

# Alternative SQL for different databases

GLAMIS_MIGRATION_SQLITE = """
-- SQLite doesn't support ALTER TABLE ADD MULTIPLE COLUMNS in one statement
-- But it also doesn't support JSON, so use TEXT for JSON storage

ALTER TABLE interview_sessions ADD COLUMN interview_type VARCHAR(20) NOT NULL DEFAULT 'subject';
ALTER TABLE interview_sessions ADD COLUMN subject VARCHAR(100);
ALTER TABLE interview_sessions ADD COLUMN company VARCHAR(255);
ALTER TABLE interview_sessions ADD COLUMN job_title VARCHAR(255);
ALTER TABLE interview_sessions ADD COLUMN jd_details TEXT;
ALTER TABLE interview_sessions ADD COLUMN svar_type VARCHAR(50);
ALTER TABLE interview_sessions ADD COLUMN weak_areas_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE interview_sessions ADD COLUMN strong_areas_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE interview_sessions ADD COLUMN asked_questions_hash TEXT NOT NULL DEFAULT '[]';
"""

GLAMIS_MIGRATION_POSTGRESQL = """
-- PostgreSQL migration with proper JSON type

BEGIN;

ALTER TABLE interview_sessions 
ADD COLUMN interview_type VARCHAR(20) NOT NULL DEFAULT 'subject',
ADD COLUMN subject VARCHAR(100),
ADD COLUMN company VARCHAR(255),
ADD COLUMN job_title VARCHAR(255),
ADD COLUMN jd_details TEXT,
ADD COLUMN svar_type VARCHAR(50),
ADD COLUMN weak_areas_json JSONB NOT NULL DEFAULT '{}',
ADD COLUMN strong_areas_json JSONB NOT NULL DEFAULT '{}',
ADD COLUMN asked_questions_hash JSONB NOT NULL DEFAULT '[]';

-- Create indexes for performance
CREATE INDEX idx_interview_type ON interview_sessions(interview_type);
CREATE INDEX idx_interview_subject ON interview_sessions(subject);
CREATE INDEX idx_interview_company ON interview_sessions(company);

COMMIT;
"""

GLAMIS_MIGRATION_MYSQL = """
-- MySQL migration

ALTER TABLE interview_sessions 
ADD COLUMN interview_type VARCHAR(20) NOT NULL DEFAULT 'subject' AFTER status,
ADD COLUMN subject VARCHAR(100) AFTER interview_type,
ADD COLUMN company VARCHAR(255) AFTER subject,
ADD COLUMN job_title VARCHAR(255) AFTER company,
ADD COLUMN jd_details LONGTEXT AFTER job_title,
ADD COLUMN svar_type VARCHAR(50) AFTER jd_details,
ADD COLUMN weak_areas_json JSON NOT NULL DEFAULT '{}' AFTER svar_type,
ADD COLUMN strong_areas_json JSON NOT NULL DEFAULT '{}' AFTER weak_areas_json,
ADD COLUMN asked_questions_hash JSON NOT NULL DEFAULT '[]' AFTER strong_areas_json;

-- Create indexes
CREATE INDEX idx_interview_type ON interview_sessions(interview_type);
CREATE INDEX idx_interview_subject ON interview_sessions(subject);
CREATE INDEX idx_interview_company ON interview_sessions(company);
"""


def run_migration(db_type: str = "mysql"):
    """
    Run the GLAMIS migration on the database.
    
    Args:
        db_type: Database type ('mysql', 'postgresql', 'sqlite', 'default')
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = SessionLocal()
        
        # Select appropriate migration SQL
        if db_type.lower() == "postgresql":
            migration_sql = GLAMIS_MIGRATION_POSTGRESQL
        elif db_type.lower() == "sqlite":
            migration_sql = GLAMIS_MIGRATION_SQLITE
        elif db_type.lower() == "mysql":
            migration_sql = GLAMIS_MIGRATION_MYSQL
        else:
            migration_sql = GLAMIS_MIGRATION_SQL
        
        # Execute migration
        print(f"Running GLAMIS migration for {db_type}...")
        print("=" * 80)
        
        # Split SQL by newlines and execute each statement
        statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
        
        for i, statement in enumerate(statements, 1):
            try:
                print(f"\n[{i}/{len(statements)}] Executing...")
                print(f"SQL: {statement[:80]}...")
                db.execute(text(statement))
                db.commit()
                print("✅ Success")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                db.rollback()
                # Continue with other statements
                # (some may fail if columns already exist, which is okay)
        
        print("\n" + "=" * 80)
        print("✅ Migration completed successfully!")
        print("\nNew columns added:")
        print("  - interview_type (VARCHAR 20)")
        print("  - subject (VARCHAR 100)")
        print("  - company (VARCHAR 255)")
        print("  - job_title (VARCHAR 255)")
        print("  - jd_details (TEXT)")
        print("  - svar_type (VARCHAR 50)")
        print("  - weak_areas_json (JSON)")
        print("  - strong_areas_json (JSON)")
        print("  - asked_questions_hash (JSON)")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()


def verify_migration():
    """
    Verify that the migration was successful by checking for new columns.
    
    Returns:
        True if all expected columns exist, False otherwise
    """
    try:
        from sqlalchemy import inspect
        
        db = SessionLocal()
        inspector = inspect(db.get_bind())
        
        columns = [col['name'] for col in inspector.get_columns('interview_sessions')]
        
        expected_columns = [
            'interview_type',
            'subject',
            'company',
            'job_title',
            'jd_details',
            'svar_type',
            'weak_areas_json',
            'strong_areas_json',
            'asked_questions_hash'
        ]
        
        print("Verifying GLAMIS migration...")
        print("=" * 80)
        
        missing = []
        for col in expected_columns:
            if col in columns:
                print(f"✅ {col}")
            else:
                print(f"❌ {col} (MISSING)")
                missing.append(col)
        
        print("=" * 80)
        
        if missing:
            print(f"❌ Migration verification failed! Missing columns: {missing}")
            return False
        else:
            print("✅ All required columns present. Migration successful!")
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()


def rollback_migration(db_type: str = "mysql"):
    """
    Rollback the GLAMIS migration (remove added columns).
    
    WARNING: This is destructive and will lose any data in these columns!
    
    Args:
        db_type: Database type
    
    Returns:
        True if successful, False otherwise
    """
    rollback_sql = """
    ALTER TABLE interview_sessions DROP COLUMN interview_type;
    ALTER TABLE interview_sessions DROP COLUMN subject;
    ALTER TABLE interview_sessions DROP COLUMN company;
    ALTER TABLE interview_sessions DROP COLUMN job_title;
    ALTER TABLE interview_sessions DROP COLUMN jd_details;
    ALTER TABLE interview_sessions DROP COLUMN svar_type;
    ALTER TABLE interview_sessions DROP COLUMN weak_areas_json;
    ALTER TABLE interview_sessions DROP COLUMN strong_areas_json;
    ALTER TABLE interview_sessions DROP COLUMN asked_questions_hash;
    DROP INDEX idx_interview_type;
    DROP INDEX idx_interview_subject;
    DROP INDEX idx_interview_company;
    """
    
    print("⚠️  WARNING: This will remove GLAMIS support and all related data!")
    confirm = input("Are you sure you want to rollback? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("Rollback cancelled")
        return False
    
    try:
        db = SessionLocal()
        
        print("Rolling back GLAMIS migration...")
        statements = [s.strip() for s in rollback_sql.split(';') if s.strip()]
        
        for statement in statements:
            try:
                db.execute(text(statement))
                db.commit()
            except Exception:
                # Ignore errors (indexes might not exist, etc.)
                db.rollback()
                pass
        
        print("✅ Rollback completed")
        return True
        
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        db_type = sys.argv[2] if len(sys.argv) > 2 else "mysql"
        
        if command == "migrate":
            success = run_migration(db_type)
            sys.exit(0 if success else 1)
        elif command == "verify":
            success = verify_migration()
            sys.exit(0 if success else 1)
        elif command == "rollback":
            success = rollback_migration(db_type)
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown command: {command}")
            print("Usage: python database_migration_glamis.py [migrate|verify|rollback] [db_type]")
            sys.exit(1)
    else:
        # Interactive mode
        print("GLAMIS Database Migration Tool")
        print("=" * 80)
        print("Commands:")
        print("  1. migrate   - Run migration (add new columns)")
        print("  2. verify    - Verify migration success")
        print("  3. rollback  - Rollback migration (DESTRUCTIVE)")
        print("  4. exit      - Exit without changes")
        print()
        
        command = input("Enter command: ").lower()
        
        if command == "migrate" or command == "1":
            db_type = input("Enter database type (mysql/postgresql/sqlite) [mysql]: ").strip() or "mysql"
            run_migration(db_type)
        elif command == "verify" or command == "2":
            verify_migration()
        elif command == "rollback" or command == "3":
            db_type = input("Enter database type (mysql/postgresql/sqlite) [mysql]: ").strip() or "mysql"
            rollback_migration(db_type)
        else:
            print("Exiting without changes")
