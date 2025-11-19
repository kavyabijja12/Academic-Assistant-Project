"""
View and manage student appointments
Run this script to see all appointments for a student
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database.Database import get_session
from database.models import Appointment, Student, Advisor

def view_student_appointments(student_id: str):
    """View all appointments for a student"""
    db = get_session()
    try:
        student = db.query(Student).filter(Student.asu_id == student_id).first()
        if not student:
            print(f"Student with ASU ID {student_id} not found.")
            return
        
        print(f"\n{'='*70}")
        print(f"Appointments for: {student.name} (ASU ID: {student_id})")
        print(f"{'='*70}\n")
        
        appointments = db.query(Appointment).filter(
            Appointment.student_id == student_id
        ).order_by(Appointment.slot_datetime.asc()).all()
        
        if not appointments:
            print("No appointments found.")
            return
        
        # Group by status
        pending = [a for a in appointments if a.status == 'pending']
        confirmed = [a for a in appointments if a.status == 'confirmed']
        cancelled = [a for a in appointments if a.status == 'cancelled']
        
        print(f"Total Appointments: {len(appointments)}")
        print(f"  - Pending: {len(pending)}")
        print(f"  - Confirmed: {len(confirmed)}")
        print(f"  - Cancelled: {len(cancelled)}\n")
        
        # Show pending and confirmed
        active = [a for a in appointments if a.status in ['pending', 'confirmed']]
        if active:
            print("Active Appointments (Pending/Confirmed):")
            print("-" * 70)
            for appt in active:
                advisor = db.query(Advisor).filter(Advisor.advisor_id == appt.advisor_id).first()
                advisor_name = advisor.name if advisor else "Unknown"
                date_str = appt.slot_datetime.strftime("%A, %B %d, %Y")
                time_str = appt.slot_datetime.strftime("%I:%M %p")
                print(f"  ID: {appt.appointment_id[:8]}...")
                print(f"  Advisor: {advisor_name}")
                print(f"  Date/Time: {date_str} at {time_str}")
                print(f"  Status: {appt.status.upper()}")
                print()
        
        # Show cancelled (if any)
        if cancelled:
            print("\nCancelled Appointments:")
            print("-" * 70)
            for appt in cancelled[:5]:  # Show first 5
                advisor = db.query(Advisor).filter(Advisor.advisor_id == appt.advisor_id).first()
                advisor_name = advisor.name if advisor else "Unknown"
                date_str = appt.slot_datetime.strftime("%A, %B %d, %Y")
                time_str = appt.slot_datetime.strftime("%I:%M %p")
                print(f"  {date_str} at {time_str} with {advisor_name} (CANCELLED)")
            if len(cancelled) > 5:
                print(f"  ... and {len(cancelled) - 5} more cancelled appointments")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

def list_all_appointments():
    """List all appointments in the database"""
    db = get_session()
    try:
        appointments = db.query(Appointment).order_by(Appointment.slot_datetime.asc()).all()
        
        print(f"\n{'='*70}")
        print(f"All Appointments in Database")
        print(f"{'='*70}\n")
        print(f"Total: {len(appointments)} appointments\n")
        
        # Group by student
        from collections import defaultdict
        by_student = defaultdict(list)
        for appt in appointments:
            by_student[appt.student_id].append(appt)
        
        for student_id, appts in by_student.items():
            student = db.query(Student).filter(Student.asu_id == student_id).first()
            student_name = student.name if student else "Unknown"
            print(f"{student_name} ({student_id}): {len(appts)} appointments")
            for appt in appts[:3]:  # Show first 3
                date_str = appt.slot_datetime.strftime("%Y-%m-%d %I:%M %p")
                print(f"  - {date_str} ({appt.status})")
            if len(appts) > 3:
                print(f"  ... and {len(appts) - 3} more")
            print()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        student_id = sys.argv[1]
        view_student_appointments(student_id)
    else:
        # Default: show appointments for test student
        print("Usage: python view_appointments.py [ASU_ID]")
        print("\nShowing appointments for test student (1231777770):\n")
        view_student_appointments("1231777770")
        
        print("\n" + "="*70)
        print("\nTo view all appointments in database, run:")
        print("  python -c \"from view_appointments import list_all_appointments; list_all_appointments()\"")


