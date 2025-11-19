"""
Test script for Calendar Service
Run this to verify calendar functionality
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.CalendarService import CalendarService


def test_working_hours():
    """Test getting working hours"""
    print("Testing working hours...")
    calendar = CalendarService()
    
    hours = calendar.get_working_hours("cciemnoc@asu.edu")
    
    print(f"  Start hour: {hours['start_hour']}")
    print(f"  End hour: {hours['end_hour']}")
    print(f"  Days of week: {hours['days_of_week']}")
    
    if hours['start_hour'] == 8 and hours['end_hour'] == 17:
        print("  ✓ Working hours correct")
        return True
    else:
        print("  ✗ Working hours incorrect")
        return False


def test_generate_slots_for_date():
    """Test generating slots for a single date"""
    print("\nTesting slot generation for single date...")
    calendar = CalendarService()
    
    # Test with a weekday (Monday)
    test_date = date(2025, 2, 3)  # Monday
    slots = calendar.generate_slots_for_date("cciemnoc@asu.edu", test_date)
    
    print(f"  Date: {test_date.strftime('%A, %B %d, %Y')}")
    print(f"  Generated {len(slots)} slots")
    
    if len(slots) > 0:
        print(f"  First slot: {calendar.format_slot_display(slots[0])}")
        print(f"  Last slot: {calendar.format_slot_display(slots[-1])}")
        print(f"  ✓ Slots generated correctly")
        
        # Check slot duration (should be 30 minutes apart)
        if len(slots) > 1:
            diff = (slots[1] - slots[0]).total_seconds() / 60
            if diff == 30:
                print(f"  ✓ Slot duration correct (30 minutes)")
            else:
                print(f"  ✗ Slot duration incorrect: {diff} minutes")
                return False
    else:
        print(f"  ✗ No slots generated")
        return False
    
    # Test with weekend (should return empty)
    weekend_date = date(2025, 2, 1)  # Saturday
    weekend_slots = calendar.generate_slots_for_date("cciemnoc@asu.edu", weekend_date)
    if len(weekend_slots) == 0:
        print(f"  ✓ Weekend correctly excluded")
    else:
        print(f"  ✗ Weekend slots generated (should be empty)")
        return False
    
    return True


def test_generate_slots_for_range():
    """Test generating slots for a date range"""
    print("\nTesting slot generation for date range...")
    calendar = CalendarService()
    
    start_date = date(2025, 2, 3)  # Monday
    end_date = date(2025, 2, 7)    # Friday
    
    slots = calendar.generate_slots_for_date_range("cciemnoc@asu.edu", start_date, end_date)
    
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Generated {len(slots)} slots total")
    
    # Should have slots for 5 weekdays
    # Each day: 8 AM to 5 PM = 9 hours = 18 slots (30 min each)
    expected_slots = 5 * 18  # 5 days * 18 slots per day
    
    if len(slots) == expected_slots:
        print(f"  ✓ Correct number of slots generated ({expected_slots})")
        return True
    else:
        print(f"  ✗ Incorrect number of slots: {len(slots)}, expected {expected_slots}")
        return False


def test_check_availability():
    """Test checking slot availability"""
    print("\nTesting slot availability check...")
    calendar = CalendarService()
    
    # Create a future slot
    future_date = date.today() + timedelta(days=7)
    if future_date.weekday() >= 5:  # If weekend, move to Monday
        future_date += timedelta(days=(7 - future_date.weekday()))
    
    test_slot = datetime.combine(future_date, datetime.min.time().replace(hour=10, minute=0))
    
    # Check availability (should be available initially)
    is_available = calendar.check_slot_availability("cciemnoc@asu.edu", test_slot)
    
    if is_available:
        print(f"  ✓ Slot is available: {calendar.format_slot_display(test_slot)}")
    else:
        print(f"  ✗ Slot is not available (might be in past or already booked)")
        return False
    
    # Mark as unavailable
    calendar.mark_slot_unavailable("cciemnoc@asu.edu", test_slot, "booked")
    
    # Check again (should be unavailable)
    is_available = calendar.check_slot_availability("cciemnoc@asu.edu", test_slot)
    if not is_available:
        print(f"  ✓ Slot correctly marked as unavailable")
    else:
        print(f"  ✗ Slot still shows as available after marking unavailable")
        return False
    
    # Mark as available again
    calendar.mark_slot_available("cciemnoc@asu.edu", test_slot)
    is_available = calendar.check_slot_availability("cciemnoc@asu.edu", test_slot)
    if is_available:
        print(f"  ✓ Slot correctly marked as available again")
    else:
        print(f"  ✗ Slot not available after marking as available")
        return False
    
    return True


def test_get_available_slots():
    """Test getting available slots"""
    print("\nTesting get available slots...")
    calendar = CalendarService()
    
    start_date = date.today() + timedelta(days=1)
    end_date = start_date + timedelta(days=6)  # Next week
    
    # Ensure we start on a weekday
    while start_date.weekday() >= 5:
        start_date += timedelta(days=1)
    
    available_slots = calendar.get_available_slots("cciemnoc@asu.edu", start_date, end_date)
    
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Available slots: {len(available_slots)}")
    
    if len(available_slots) > 0:
        print(f"  First available: {calendar.format_slot_display(available_slots[0])}")
        print(f"  ✓ Available slots retrieved")
        return True
    else:
        print(f"  ✗ No available slots found")
        return False


def test_format_display():
    """Test slot formatting"""
    print("\nTesting slot formatting...")
    calendar = CalendarService()
    
    test_slot = datetime(2025, 2, 3, 14, 30)  # Monday, Feb 3, 2025 at 2:30 PM
    
    formatted = calendar.format_slot_display(test_slot)
    time_only = calendar.format_slot_time_only(test_slot)
    
    print(f"  Full format: {formatted}")
    print(f"  Time only: {time_only}")
    
    if "Monday" in formatted and "2:30 PM" in formatted:
        print(f"  ✓ Formatting works correctly")
        return True
    else:
        print(f"  ✗ Formatting incorrect")
        return False


def main():
    """Run all calendar tests"""
    print("=" * 50)
    print("Calendar Service Test Suite")
    print("=" * 50)
    
    results = []
    
    results.append(("Working Hours", test_working_hours()))
    results.append(("Generate Slots (Single Date)", test_generate_slots_for_date()))
    results.append(("Generate Slots (Date Range)", test_generate_slots_for_range()))
    results.append(("Check Availability", test_check_availability()))
    results.append(("Get Available Slots", test_get_available_slots()))
    results.append(("Format Display", test_format_display()))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All calendar tests passed!")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    main()


