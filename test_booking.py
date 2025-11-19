"""
Test script for Booking Agent
Run this to verify booking functionality
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.BookingAgent import BookingAgent
from services.CalendarService import CalendarService


def test_get_available_slots():
    """Test getting available slots"""
    print("Testing get available slots...")
    booking = BookingAgent()
    
    start_date = date.today() + timedelta(days=1)
    end_date = start_date + timedelta(days=6)
    
    # Ensure we start on a weekday
    while start_date.weekday() >= 5:
        start_date += timedelta(days=1)
    
    slots = booking.get_available_slots("cciemnoc@asu.edu", start_date, end_date)
    
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Available slots: {len(slots)}")
    
    if len(slots) > 0:
        calendar = CalendarService()
        print(f"  First slot: {calendar.format_slot_display(slots[0])}")
        print(f"  ✓ Available slots retrieved")
        return True
    else:
        print(f"  ✗ No available slots found")
        return False


def test_book_appointment():
    """Test booking an appointment"""
    print("\nTesting book appointment...")
    booking = BookingAgent()
    
    # Get an available slot
    start_date = date.today() + timedelta(days=1)
    while start_date.weekday() >= 5:
        start_date += timedelta(days=1)
    
    end_date = start_date + timedelta(days=1)
    slots = booking.get_available_slots("cciemnoc@asu.edu", start_date, end_date)
    
    if len(slots) == 0:
        print(f"  ✗ No available slots to test booking")
        return False
    
    test_slot = slots[0]
    
    # Book appointment
    result = booking.book_appointment(
        student_id="1231777770",
        advisor_id="cciemnoc@asu.edu",
        slot_datetime=test_slot,
        reason="Test appointment"
    )
    
    if result["success"]:
        print(f"  ✓ Appointment booked successfully")
        print(f"    Appointment ID: {result['appointment'].appointment_id}")
        print(f"    Status: {result['appointment'].status}")
        
        # Verify slot is no longer available
        calendar = CalendarService()
        is_available = calendar.check_slot_availability("cciemnoc@asu.edu", test_slot)
        if not is_available:
            print(f"  ✓ Slot correctly marked as unavailable")
        else:
            print(f"  ✗ Slot still shows as available")
            return False
        
        return result["appointment"]
    else:
        print(f"  ✗ Failed to book appointment: {result['message']}")
        return False


def test_book_duplicate():
    """Test booking duplicate appointment"""
    print("\nTesting duplicate appointment prevention...")
    booking = BookingAgent()
    
    # Get an available slot
    start_date = date.today() + timedelta(days=1)
    while start_date.weekday() >= 5:
        start_date += timedelta(days=1)
    
    end_date = start_date + timedelta(days=1)
    slots = booking.get_available_slots("cciemnoc@asu.edu", start_date, end_date)
    
    if len(slots) == 0:
        print(f"  ✗ No available slots to test")
        return False
    
    test_slot = slots[0]
    
    # Book first appointment
    result1 = booking.book_appointment(
        student_id="1231777770",
        advisor_id="cciemnoc@asu.edu",
        slot_datetime=test_slot
    )
    
    if not result1["success"]:
        print(f"  ✗ Failed to book first appointment")
        return False
    
    # Try to book same slot again (should fail)
    result2 = booking.book_appointment(
        student_id="1231777770",
        advisor_id="cciemnoc@asu.edu",
        slot_datetime=test_slot
    )
    
    if not result2["success"]:
        print(f"  ✓ Duplicate booking correctly prevented")
        return True
    else:
        print(f"  ✗ Duplicate booking was allowed (should be prevented)")
        return False


def test_get_student_appointments(appointment):
    """Test getting student appointments"""
    print("\nTesting get student appointments...")
    booking = BookingAgent()
    
    appointments = booking.get_student_appointments("1231777770")
    
    print(f"  Found {len(appointments)} appointments for student")
    
    if len(appointments) > 0:
        calendar = CalendarService()
        for appt in appointments[:3]:  # Show first 3
            formatted = calendar.format_slot_display(appt.slot_datetime)
            print(f"    - {formatted} ({appt.status})")
        print(f"  ✓ Student appointments retrieved")
        return True
    else:
        print(f"  ✗ No appointments found")
        return False


def test_cancel_appointment(appointment):
    """Test cancelling an appointment"""
    print("\nTesting cancel appointment...")
    booking = BookingAgent()
    
    if not appointment:
        print(f"  ✗ No appointment to cancel")
        return False
    
    appointment_id = appointment.appointment_id
    slot_datetime = appointment.slot_datetime
    
    # Cancel appointment
    result = booking.cancel_appointment(appointment_id, "1231777770")
    
    if result["success"]:
        print(f"  ✓ Appointment cancelled successfully")
        
        # Verify slot is available again
        calendar = CalendarService()
        is_available = calendar.check_slot_availability("cciemnoc@asu.edu", slot_datetime)
        if is_available:
            print(f"  ✓ Slot correctly marked as available again")
        else:
            print(f"  ✗ Slot still shows as unavailable")
            return False
        
        return True
    else:
        print(f"  ✗ Failed to cancel appointment: {result['message']}")
        return False


def test_confirm_appointment():
    """Test confirming an appointment"""
    print("\nTesting confirm appointment...")
    booking = BookingAgent()
    
    # Book a new appointment
    start_date = date.today() + timedelta(days=1)
    while start_date.weekday() >= 5:
        start_date += timedelta(days=1)
    
    end_date = start_date + timedelta(days=1)
    slots = booking.get_available_slots("cciemnoc@asu.edu", start_date, end_date)
    
    if len(slots) == 0:
        print(f"  ✗ No available slots to test")
        return False
    
    result = booking.book_appointment(
        student_id="1231777770",
        advisor_id="cciemnoc@asu.edu",
        slot_datetime=slots[0]
    )
    
    if not result["success"]:
        print(f"  ✗ Failed to book appointment for confirmation test")
        return False
    
    appointment_id = result["appointment"].appointment_id
    
    # Confirm appointment
    confirm_result = booking.confirm_appointment(appointment_id)
    
    if confirm_result["success"]:
        print(f"  ✓ Appointment confirmed successfully")
        print(f"    Status: {confirm_result['appointment']['status']}")
        return True
    else:
        print(f"  ✗ Failed to confirm appointment: {confirm_result['message']}")
        return False


def test_appointment_summary():
    """Test formatting appointment summary"""
    print("\nTesting appointment summary formatting...")
    booking = BookingAgent()
    
    # Get an appointment
    appointments = booking.get_student_appointments("1231777770")
    
    if len(appointments) > 0:
        summary = booking.format_appointment_summary(appointments[0])
        print(f"  Summary preview:")
        print(f"  {summary[:200]}...")
        print(f"  ✓ Appointment summary formatted")
        return True
    else:
        print(f"  ✗ No appointments to format")
        return False


def main():
    """Run all booking tests"""
    print("=" * 50)
    print("Booking Agent Test Suite")
    print("=" * 50)
    
    results = []
    test_appointment = None
    
    results.append(("Get Available Slots", test_get_available_slots()))
    test_appointment = test_book_appointment()
    results.append(("Book Appointment", test_appointment is not False))
    results.append(("Prevent Duplicate", test_book_duplicate()))
    results.append(("Get Student Appointments", test_get_student_appointments(test_appointment)))
    results.append(("Cancel Appointment", test_cancel_appointment(test_appointment)))
    results.append(("Confirm Appointment", test_confirm_appointment()))
    results.append(("Appointment Summary", test_appointment_summary()))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All booking tests passed!")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    main()

