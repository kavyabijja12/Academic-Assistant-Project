"""
Test script for Agent Controller
Run this to verify routing functionality
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.AgentController import AgentController


def test_route_booking_intent():
    """Test routing booking intent"""
    print("Testing route booking intent...")
    controller = AgentController()
    
    # Test without authentication
    result = controller.route_request("I want to book an appointment")
    
    if result["intent"] == "booking" and result["action"] == "require_authentication":
        print(f"  ✓ Booking intent correctly requires authentication")
    else:
        print(f"  ✗ Booking intent routing failed: {result}")
        return False
    
    # Test with authentication
    student_context = {
        "authenticated": True,
        "asu_id": "1231777770",
        "program_level": "undergraduate"
    }
    
    result = controller.route_request("book appointment", student_context)
    
    if result["intent"] == "booking" and result["action"] == "start_booking":
        print(f"  ✓ Authenticated booking correctly starts booking flow")
        return True
    else:
        print(f"  ✗ Authenticated booking routing failed: {result}")
        return False


def test_route_question_intent():
    """Test routing question intent"""
    print("\nTesting route question intent...")
    controller = AgentController()
    
    result = controller.route_request("what are the graduation requirements?")
    
    if result["intent"] == "question" and result["action"] == "ask_question":
        print(f"  ✓ Question intent correctly routes to RAG system")
        return True
    else:
        print(f"  ✗ Question intent routing failed: {result}")
        return False


def test_get_available_advisors():
    """Test getting advisors by program level"""
    print("\nTesting get available advisors...")
    controller = AgentController()
    
    # Test undergraduate advisors
    ug_advisors = controller.get_available_advisors("undergraduate")
    print(f"  Undergraduate advisors: {len(ug_advisors)}")
    
    if len(ug_advisors) == 7:
        print(f"  ✓ Correct number of undergraduate advisors")
        print(f"    Example: {ug_advisors[0]['name']}")
    else:
        print(f"  ✗ Incorrect number: {len(ug_advisors)}, expected 7")
        return False
    
    # Test graduate advisors
    grad_advisors = controller.get_available_advisors("graduate")
    print(f"  Graduate advisors: {len(grad_advisors)}")
    
    if len(grad_advisors) == 3:
        print(f"  ✓ Correct number of graduate advisors")
        print(f"    Example: {grad_advisors[0]['name']}")
    else:
        print(f"  ✗ Incorrect number: {len(grad_advisors)}, expected 3")
        return False
    
    return True


def test_handle_booking_request():
    """Test handling booking request"""
    print("\nTesting handle booking request...")
    controller = AgentController()
    
    result = controller.handle_booking_request("1231777770", "book appointment")
    
    if result["success"]:
        print(f"  ✓ Booking request handled successfully")
        print(f"    Student: {result['student']['name']}")
        print(f"    Program: {result['student']['program_level']}")
        return True
    else:
        print(f"  ✗ Failed to handle booking request: {result['message']}")
        return False


def test_process_booking_flow():
    """Test complete booking flow"""
    print("\nTesting process booking flow...")
    controller = AgentController()
    
    # Get an available slot
    from services.CalendarService import CalendarService
    calendar = CalendarService()
    
    start_date = date.today() + timedelta(days=1)
    while start_date.weekday() >= 5:
        start_date += timedelta(days=1)
    
    end_date = start_date + timedelta(days=1)
    slots = calendar.get_available_slots("cciemnoc@asu.edu", start_date, end_date)
    
    if len(slots) == 0:
        print(f"  ⚠ No available slots to test")
        return None
    
    test_slot = slots[0]
    
    result = controller.process_booking_flow(
        student_id="1231777770",
        advisor_id="cciemnoc@asu.edu",
        slot_datetime=test_slot,
        reason="Test booking flow"
    )
    
    if result["success"]:
        print(f"  ✓ Booking flow completed successfully")
        print(f"    Appointment ID: {result['appointment'].appointment_id}")
        print(f"    Email sent: {result.get('email_sent', False)}")
        return True
    else:
        print(f"  ✗ Booking flow failed: {result['message']}")
        return False


def main():
    """Run all agent controller tests"""
    print("=" * 50)
    print("Agent Controller Test Suite")
    print("=" * 50)
    
    results = []
    
    results.append(("Route Booking Intent", test_route_booking_intent()))
    results.append(("Route Question Intent", test_route_question_intent()))
    results.append(("Get Available Advisors", test_get_available_advisors()))
    results.append(("Handle Booking Request", test_handle_booking_request()))
    booking_flow_result = test_process_booking_flow()
    if booking_flow_result is not None:
        results.append(("Process Booking Flow", booking_flow_result))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        if result is None:
            status = "⚠ SKIPPED"
        elif result:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
        print(f"{test_name}: {status}")
    
    # Only count non-skipped tests
    non_skipped = [r for r in results if r[1] is not None]
    all_passed = all(result for _, result in non_skipped) if non_skipped else False
    
    if all_passed and non_skipped:
        print("\n✓ All agent controller tests passed!")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    main()


