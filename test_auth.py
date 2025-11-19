"""
Test script for Authentication Agent
Run this to verify authentication functionality
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.AuthenticationAgent import AuthenticationAgent


def test_password_hashing():
    """Test password hashing and verification"""
    print("Testing password hashing...")
    auth = AuthenticationAgent()
    
    password = "test123"
    hashed = auth.hash_password(password)
    
    print(f"  Original password: {password}")
    print(f"  Hashed password: {hashed[:50]}...")
    
    # Test verification
    is_valid = auth.verify_password(password, hashed)
    is_invalid = auth.verify_password("wrongpassword", hashed)
    
    if is_valid and not is_invalid:
        print("  ✓ Password hashing and verification works")
        return True
    else:
        print("  ✗ Password hashing failed")
        return False


def test_authentication():
    """Test student authentication"""
    print("\nTesting authentication...")
    auth = AuthenticationAgent()
    
    # Test with correct credentials (test student from init_db.py)
    result = auth.authenticate("1231777770", "test123")
    
    if result["success"]:
        print(f"  ✓ Authentication successful")
        print(f"    Student: {result['student'].name}")
        print(f"    Email: {result['student'].email}")
        print(f"    Program: {result['student'].program_level}")
    else:
        print(f"  ✗ Authentication failed: {result['message']}")
        return False
    
    # Test with wrong password
    result = auth.authenticate("1231777770", "wrongpassword")
    if not result["success"]:
        print(f"  ✓ Invalid password correctly rejected")
    else:
        print(f"  ✗ Invalid password was accepted (security issue!)")
        return False
    
    # Test with non-existent student
    result = auth.authenticate("9999999999", "test123")
    if not result["success"]:
        print(f"  ✓ Non-existent student correctly rejected")
    else:
        print(f"  ✗ Non-existent student was accepted")
        return False
    
    return True


def test_get_student_info():
    """Test getting student information"""
    print("\nTesting get student info...")
    auth = AuthenticationAgent()
    
    student = auth.get_student_info("1231777770")
    
    if student:
        print(f"  ✓ Student info retrieved:")
        print(f"    ASU ID: {student.asu_id}")
        print(f"    Name: {student.name}")
        print(f"    Email: {student.email}")
        print(f"    Program: {student.program_level}")
        return True
    else:
        print(f"  ✗ Failed to get student info")
        return False


def test_create_student():
    """Test creating a new student"""
    print("\nTesting create student...")
    auth = AuthenticationAgent()
    
    import random
    # Use random ID to avoid conflicts from previous test runs
    test_asu_id = f"999{random.randint(100000, 999999)}"
    test_email = f"test.student.{random.randint(1000, 9999)}@asu.edu"
    
    # Try to create a new student
    result = auth.create_student(
        asu_id=test_asu_id,
        email=test_email,
        name="Test Student",
        password="testpass123",
        program_level="undergraduate"
    )
    
    if result["success"]:
        print(f"  ✓ Student created successfully")
        print(f"    ASU ID: {result['student']['asu_id']}")
        print(f"    Name: {result['student']['name']}")
        
        # Test authentication with new student
        auth_result = auth.authenticate(test_asu_id, "testpass123")
        if auth_result["success"]:
            print(f"  ✓ New student can authenticate")
        else:
            print(f"  ✗ New student cannot authenticate")
            return False
        
        # Test duplicate creation (should fail)
        duplicate_result = auth.create_student(
            asu_id=test_asu_id,
            email=test_email,
            name="Duplicate Test",
            password="testpass123",
            program_level="undergraduate"
        )
        if not duplicate_result["success"]:
            print(f"  ✓ Duplicate student correctly rejected")
        else:
            print(f"  ✗ Duplicate student was created (should be rejected)")
            return False
        
        return True
    else:
        print(f"  ✗ Failed to create student: {result['message']}")
        return False


def test_update_password():
    """Test password update"""
    print("\nTesting password update...")
    auth = AuthenticationAgent()
    
    import random
    # Create a fresh test student for password update
    test_asu_id = f"888{random.randint(100000, 999999)}"
    test_email = f"password.test.{random.randint(1000, 9999)}@asu.edu"
    
    # First create a test student
    create_result = auth.create_student(
        asu_id=test_asu_id,
        email=test_email,
        name="Password Test",
        password="oldpass123",
        program_level="graduate"
    )
    
    if not create_result["success"]:
        print(f"  ✗ Failed to create test student: {create_result['message']}")
        return False
    
    # Update password
    result = auth.update_student_password(test_asu_id, "oldpass123", "newpass123")
    
    if result["success"]:
        print(f"  ✓ Password updated successfully")
        
        # Test old password doesn't work
        auth_result = auth.authenticate(test_asu_id, "oldpass123")
        if not auth_result["success"]:
            print(f"  ✓ Old password correctly rejected")
        else:
            print(f"  ✗ Old password still works (security issue!)")
            return False
        
        # Test new password works
        auth_result = auth.authenticate(test_asu_id, "newpass123")
        if auth_result["success"]:
            print(f"  ✓ New password works")
        else:
            print(f"  ✗ New password doesn't work")
            return False
        
        return True
    else:
        print(f"  ✗ Failed to update password: {result['message']}")
        return False


def main():
    """Run all authentication tests"""
    print("=" * 50)
    print("Authentication Agent Test Suite")
    print("=" * 50)
    
    results = []
    
    results.append(("Password Hashing", test_password_hashing()))
    results.append(("Authentication", test_authentication()))
    results.append(("Get Student Info", test_get_student_info()))
    results.append(("Create Student", test_create_student()))
    results.append(("Update Password", test_update_password()))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All authentication tests passed!")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    main()

