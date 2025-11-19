"""
Test script for Intent Classifier
Run this to verify intent detection functionality
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.IntentClassifier import IntentClassifier


def test_booking_intent():
    """Test booking intent detection"""
    print("Testing booking intent detection...")
    classifier = IntentClassifier()
    
    booking_phrases = [
        "I want to book an appointment",
        "schedule a meeting with my advisor",
        "book appointment",
        "I need to see an advisor",
        "can I make an appointment?",
        "set up a meeting",
        "reserve a time slot"
    ]
    
    all_correct = True
    for phrase in booking_phrases:
        result = classifier.detect_intent(phrase)
        if result["intent"] == "booking":
            print(f"  ✓ '{phrase}' → booking ({result['confidence']})")
        else:
            print(f"  ✗ '{phrase}' → {result['intent']} (should be booking)")
            all_correct = False
    
    return all_correct


def test_question_intent():
    """Test question intent detection"""
    print("\nTesting question intent detection...")
    classifier = IntentClassifier()
    
    question_phrases = [
        "what are the graduation requirements?",
        "tell me about the IT program",
        "how do I apply?",
        "what courses are required?",
        "explain the capstone project",
        "information about advisors"
    ]
    
    all_correct = True
    for phrase in question_phrases:
        result = classifier.detect_intent(phrase)
        if result["intent"] == "question":
            print(f"  ✓ '{phrase}' → question ({result['confidence']})")
        else:
            print(f"  ✗ '{phrase}' → {result['intent']} (should be question)")
            all_correct = False
    
    return all_correct


def test_ambiguous_intent():
    """Test ambiguous intent (needs LLM)"""
    print("\nTesting ambiguous intent (using LLM)...")
    classifier = IntentClassifier()
    
    ambiguous_phrases = [
        "I need help with my schedule",
        "can you help me?",
        "I want to talk about my courses"
    ]
    
    for phrase in ambiguous_phrases:
        result = classifier.detect_intent(phrase)
        print(f"  '{phrase}' → {result['intent']} ({result['confidence']})")
        print(f"    Reasoning: {result['reasoning']}")
    
    return True  # Just checking it doesn't crash


def test_edge_cases():
    """Test edge cases"""
    print("\nTesting edge cases...")
    classifier = IntentClassifier()
    
    # Empty input
    result = classifier.detect_intent("")
    if result["intent"] == "question":
        print(f"  ✓ Empty input handled")
    else:
        print(f"  ✗ Empty input not handled correctly")
        return False
    
    # Very short input
    result = classifier.detect_intent("hi")
    print(f"  'hi' → {result['intent']} ({result['confidence']})")
    
    return True


def main():
    """Run all intent classifier tests"""
    print("=" * 50)
    print("Intent Classifier Test Suite")
    print("=" * 50)
    
    results = []
    
    results.append(("Booking Intent", test_booking_intent()))
    results.append(("Question Intent", test_question_intent()))
    results.append(("Ambiguous Intent", test_ambiguous_intent()))
    results.append(("Edge Cases", test_edge_cases()))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All intent classifier tests passed!")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    main()


