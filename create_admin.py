"""
Create an admin account
Run this script to create an admin user for the dashboard
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database.Database import init_database, get_session
from database.models import Admin
from agents.AuthenticationAgent import AuthenticationAgent

def create_admin():
    """Create an admin account"""
    # Initialize database to ensure Admin table exists
    init_database()
    
    auth_agent = AuthenticationAgent()
    
    # Default admin credentials (change these!)
    admin_id = "admin"
    email = "admin@asu.edu"
    name = "Admin User"
    password = "admin123"  # Change this in production!
    
    print("Creating admin account...")
    result = auth_agent.create_admin(admin_id, email, name, password)
    
    if result["success"]:
        print("\n✅ Admin account created successfully!")
        print(f"\nAdmin ID: {admin_id}")
        print(f"Email: {email}")
        print(f"Name: {name}")
        print(f"Password: {password}")
        print("\n⚠️  Please change the default password after first login!")
    else:
        print(f"\n❌ Error: {result['message']}")
        # Check if admin already exists
        db = get_session()
        try:
            existing = db.query(Admin).filter(
                (Admin.admin_id == admin_id) | (Admin.email == email)
            ).first()
            if existing:
                print(f"\nAdmin already exists with ID: {existing.admin_id}")
        finally:
            db.close()


if __name__ == "__main__":
    create_admin()



