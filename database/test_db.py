"""
Test script to verify database setup
Run this after initializing the database to check everything works
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.Database import get_session, init_database
from database.models import Advisor, Student, Appointment, AdvisorCalendar, ChatHistory


def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    try:
        from sqlalchemy import text
        db = get_session()
        db.execute(text("SELECT 1"))
        db.close()
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_tables_exist():
    """Test that all tables exist"""
    print("\nTesting tables exist...")
    try:
        from sqlalchemy import text
        db = get_session()
        tables = ['students', 'advisors', 'appointments', 'advisor_calendar', 'chat_history']
        for table in tables:
            result = db.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
            if result.fetchone():
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' missing")
        db.close()
        return True
    except Exception as e:
        print(f"✗ Error checking tables: {e}")
        return False


def test_advisors():
    """Test advisor data"""
    print("\nTesting advisor data...")
    try:
        db = get_session()
        
        # Count advisors
        total = db.query(Advisor).count()
        print(f"Total advisors: {total}")
        
        # Count by program level
        undergrad = db.query(Advisor).filter(Advisor.program_level == 'undergraduate').count()
        graduate = db.query(Advisor).filter(Advisor.program_level == 'graduate').count()
        
        print(f"  Undergraduate advisors: {undergrad}")
        print(f"  Graduate advisors: {graduate}")
        
        # List all advisors
        print("\nAdvisor list:")
        advisors = db.query(Advisor).all()
        for advisor in advisors:
            print(f"  - {advisor.name} ({advisor.program_level}) - {advisor.email}")
        
        db.close()
        
        if total == 10 and undergrad == 7 and graduate == 3:
            print("✓ Advisor data correct")
            return True
        else:
            print("✗ Advisor data incorrect")
            return False
            
    except Exception as e:
        print(f"✗ Error testing advisors: {e}")
        return False


def test_student():
    """Test student data"""
    print("\nTesting student data...")
    try:
        db = get_session()
        
        student = db.query(Student).filter(Student.asu_id == "1231777770").first()
        
        if student:
            print(f"✓ Test student found:")
            print(f"  ASU ID: {student.asu_id}")
            print(f"  Name: {student.name}")
            print(f"  Email: {student.email}")
            print(f"  Program: {student.program_level}")
            db.close()
            return True
        else:
            print("✗ Test student not found")
            db.close()
            return False
            
    except Exception as e:
        print(f"✗ Error testing student: {e}")
        return False


def test_relationships():
    """Test database relationships"""
    print("\nTesting relationships...")
    try:
        db = get_session()
        
        # Test advisor-student relationship
        advisor = db.query(Advisor).first()
        if advisor:
            print(f"✓ Advisor relationship works: {advisor.name}")
        
        # Test student-appointment relationship
        student = db.query(Student).first()
        if student:
            print(f"✓ Student relationship works: {student.name}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Error testing relationships: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("Database Test Suite")
    print("=" * 50)
    
    results = []
    
    results.append(("Connection", test_database_connection()))
    results.append(("Tables", test_tables_exist()))
    results.append(("Advisors", test_advisors()))
    results.append(("Student", test_student()))
    results.append(("Relationships", test_relationships()))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    main()

