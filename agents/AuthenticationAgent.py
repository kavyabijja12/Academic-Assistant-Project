"""
Authentication Agent
Handles student authentication, password hashing, and session management
"""

import sys
from pathlib import Path
import bcrypt
from typing import Optional, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.Database import get_session
from database.models import Student


class AuthenticationAgent:
    """Handles student authentication and password management"""
    
    def __init__(self):
        """Initialize Authentication Agent"""
        pass
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against a hash
        
        Args:
            password: Plain text password to verify
            hashed: Hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            print(f"Error verifying password: {e}")
            return False
    
    def authenticate(self, asu_id: str, password: str) -> Dict:
        """
        Authenticate a student
        
        Args:
            asu_id: Student ASU ID
            password: Student password
            
        Returns:
            Dictionary with:
            - success: bool
            - student: Student object if successful, None otherwise
            - message: str (error message if failed)
        """
        db = get_session()
        try:
            # Find student by ASU ID
            student = db.query(Student).filter(Student.asu_id == asu_id).first()
            
            if not student:
                return {
                    "success": False,
                    "student": None,
                    "message": "Student not found. Please check your ASU ID."
                }
            
            # Verify password
            if not self.verify_password(password, student.password_hash):
                return {
                    "success": False,
                    "student": None,
                    "message": "Invalid password. Please try again."
                }
            
            # Authentication successful
            return {
                "success": True,
                "student": student,
                "message": "Authentication successful"
            }
            
        except Exception as e:
            return {
                "success": False,
                "student": None,
                "message": f"Authentication error: {str(e)}"
            }
        finally:
            db.close()
    
    def get_student_info(self, asu_id: str) -> Optional[Student]:
        """
        Get student information by ASU ID
        
        Args:
            asu_id: Student ASU ID
            
        Returns:
            Student object if found, None otherwise
        """
        db = get_session()
        try:
            student = db.query(Student).filter(Student.asu_id == asu_id).first()
            return student
        except Exception as e:
            print(f"Error getting student info: {e}")
            return None
        finally:
            db.close()
    
    def create_student(self, asu_id: str, email: str, name: str, password: str, program_level: str) -> Dict:
        """
        Create a new student account
        
        Args:
            asu_id: Student ASU ID
            email: Student email
            name: Student name
            password: Plain text password (will be hashed)
            program_level: 'undergraduate' or 'graduate'
            
        Returns:
            Dictionary with success status and message
        """
        db = get_session()
        try:
            # Check if student already exists
            existing = db.query(Student).filter(
                (Student.asu_id == asu_id) | (Student.email == email)
            ).first()
            
            if existing:
                return {
                    "success": False,
                    "message": "Student with this ASU ID or email already exists."
                }
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create student
            student = Student(
                asu_id=asu_id,
                email=email,
                name=name,
                password_hash=password_hash,
                program_level=program_level.lower()
            )
            
            db.add(student)
            db.commit()
            db.refresh(student)  # Refresh to ensure object is fully loaded
            
            return {
                "success": True,
                "message": "Student account created successfully",
                "student": {
                    "asu_id": student.asu_id,
                    "email": student.email,
                    "name": student.name,
                    "program_level": student.program_level
                }
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error creating student: {str(e)}"
            }
        finally:
            db.close()
    
    def update_student_password(self, asu_id: str, old_password: str, new_password: str) -> Dict:
        """
        Update student password
        
        Args:
            asu_id: Student ASU ID
            old_password: Current password
            new_password: New password
            
        Returns:
            Dictionary with success status and message
        """
        db = get_session()
        try:
            student = db.query(Student).filter(Student.asu_id == asu_id).first()
            
            if not student:
                return {
                    "success": False,
                    "message": "Student not found"
                }
            
            # Verify old password
            if not self.verify_password(old_password, student.password_hash):
                return {
                    "success": False,
                    "message": "Current password is incorrect"
                }
            
            # Update password
            student.password_hash = self.hash_password(new_password)
            db.commit()
            
            return {
                "success": True,
                "message": "Password updated successfully"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error updating password: {str(e)}"
            }
        finally:
            db.close()

