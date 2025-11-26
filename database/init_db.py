"""
Initialize database with advisor data
Run this script once to set up the database and populate advisor information
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.Database import init_database, get_session
from database.models import Advisor, Student, Admin
from datetime import datetime

# Advisor data
UNDERGRADUATE_ADVISORS = [
    {
        "advisor_id": "cciemnoc@asu.edu",
        "name": "Celia Ciemnoczolowski",
        "email": "cciemnoc@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Success Advisor Sr.",
        "program_level": "undergraduate",
        "office_location": "Sutton Hall"
    },
    {
        "advisor_id": "dalles.colby@asu.edu",
        "name": "Dalles Colby",
        "email": "dalles.colby@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Success Advisor, Sr.",
        "program_level": "undergraduate",
        "office_location": "Sutton Hall"
    },
    {
        "advisor_id": "cafilas@asu.edu",
        "name": "Cameron Filas",
        "email": "cafilas@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Success Advisor Sr.",
        "program_level": "undergraduate",
        "office_location": "Sutton Hall"
    },
    {
        "advisor_id": "alina.rambo@asu.edu",
        "name": "Alina Rambo",
        "email": "alina.rambo@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Success Advisor, Sr.",
        "program_level": "undergraduate",
        "office_location": "Sutton Hall"
    },
    {
        "advisor_id": "meaghan.shaw@asu.edu",
        "name": "Meaghan Shaw",
        "email": "meaghan.shaw@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Success Advisor, Sr.",
        "program_level": "undergraduate",
        "office_location": "Sutton Hall"
    },
    {
        "advisor_id": "Christina.Shepherd@asu.edu",
        "name": "Christina Shepherd",
        "email": "Christina.Shepherd@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Advising Coordinator",
        "program_level": "undergraduate",
        "office_location": "Sutton Hall"
    },
    {
        "advisor_id": "Michelle.M.Valenzuela@asu.edu",
        "name": "Michelle Valenzuela",
        "email": "Michelle.M.Valenzuela@asu.edu",
        "phone": "480-727-1874",
        "title": "Manager, Undergraduate IT Advising",
        "program_level": "undergraduate",
        "office_location": "Sutton Hall"
    }
]

GRADUATE_ADVISORS = [
    {
        "advisor_id": "thomas.meadows@asu.edu",
        "name": "Thomas Meadows",
        "email": "thomas.meadows@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Success Advisor, Sr.",
        "program_level": "graduate",
        "office_location": "Sutton Hall"
    },
    {
        "advisor_id": "Yemile.Moreno@asu.edu",
        "name": "Yemile Moreno",
        "email": "Yemile.Moreno@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Success Coordinator",
        "program_level": "graduate",
        "office_location": "Sutton Hall"
    },
    {
        "advisor_id": "daphne.weaver@asu.edu",
        "name": "Daphne Weaver",
        "email": "daphne.weaver@asu.edu",
        "phone": "480-727-1874",
        "title": "Academic Advisor Sr.",
        "program_level": "graduate",
        "office_location": "Sutton Hall"
    }
]


def populate_advisors():
    """Populate advisor data into database"""
    db = get_session()
    try:
        # Check if advisors already exist
        existing_count = db.query(Advisor).count()
        if existing_count > 0:
            print(f"Advisors already exist in database ({existing_count} advisors). Skipping insertion.")
            return
        
        # Insert undergraduate advisors
        for advisor_data in UNDERGRADUATE_ADVISORS:
            advisor = Advisor(**advisor_data)
            db.add(advisor)
        
        # Insert graduate advisors
        for advisor_data in GRADUATE_ADVISORS:
            advisor = Advisor(**advisor_data)
            db.add(advisor)
        
        db.commit()
        print(f"Successfully inserted {len(UNDERGRADUATE_ADVISORS)} undergraduate advisors")
        print(f"Successfully inserted {len(GRADUATE_ADVISORS)} graduate advisors")
        
    except Exception as e:
        db.rollback()
        print(f"Error populating advisors: {e}")
        raise
    finally:
        db.close()


def create_test_student():
    """Create a test student for development"""
    import bcrypt
    from database.models import Student
    
    db = get_session()
    try:
        # Check if test student exists
        test_student = db.query(Student).filter(Student.asu_id == "1231777770").first()
        if test_student:
            print("Test student already exists. Skipping creation.")
            return
        
        # Create test student
        password = "test123"  # Change this in production!
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        test_student = Student(
            asu_id="1231777770",
            email="kbijja@asu.edu",
            name="Kavya Bijja",
            password_hash=password_hash,
            program_level="undergraduate"
        )
        
        db.add(test_student)
        db.commit()
        print("Test student created:")
        print(f"  ASU ID: 1231777770")
        print(f"  Email: kbijja@asu.edu")
        print(f"  Password: test123")
        print(f"  Program: undergraduate")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating test student: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    
    print("\nPopulating advisors...")
    populate_advisors()
    
    print("\nCreating test student...")
    create_test_student()
    
    print("\nDatabase initialization complete!")

