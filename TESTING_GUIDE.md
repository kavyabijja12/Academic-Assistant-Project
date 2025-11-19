# Testing Guide

This guide explains how to test each step of the booking system implementation.

## Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Step 1 & 2: Database Setup Testing

### 1. Initialize the database:
```bash
python database/init_db.py
```

**Expected output:**
```
Initializing database...
Database initialized at: /path/to/database/appointments.db

Populating advisors...
Successfully inserted 7 undergraduate advisors
Successfully inserted 3 graduate advisors

Creating test student...
Test student created:
  ASU ID: 1231777770
  Email: kbijja@asu.edu
  Password: test123
  Program: undergraduate

Database initialization complete!
```

### 2. Run database tests:
```bash
python database/test_db.py
```

**Expected output:**
```
==================================================
Database Test Suite
==================================================
Testing database connection...
✓ Database connection successful

Testing tables exist...
✓ Table 'students' exists
✓ Table 'advisors' exists
✓ Table 'appointments' exists
✓ Table 'advisor_calendar' exists
✓ Table 'chat_history' exists

Testing advisor data...
Total advisors: 10
  Undergraduate advisors: 7
  Graduate advisors: 3

Advisor list:
  - Celia Ciemnoczolowski (undergraduate) - cciemnoc@asu.edu
  - Dalles Colby (undergraduate) - dalles.colby@asu.edu
  ... (all 10 advisors)

✓ Advisor data correct

Testing student data...
✓ Test student found:
  ASU ID: 1231777770
  Name: Kavya Bijja
  Email: kbijja@asu.edu
  Program: undergraduate

Testing relationships...
✓ Advisor relationship works: Celia Ciemnoczolowski
✓ Student relationship works: Kavya Bijja

==================================================
Test Results Summary
==================================================
Connection: ✓ PASS
Tables: ✓ PASS
Advisors: ✓ PASS
Student: ✓ PASS
Relationships: ✓ PASS

✓ All tests passed!
```

### 3. Manual database inspection (optional):
```bash
# Using SQLite command line
sqlite3 database/appointments.db

# Then run SQL queries:
.tables
SELECT * FROM advisors;
SELECT * FROM students;
.quit
```

---

## Step 3: Authentication Agent Testing

After implementing Authentication Agent, test with:

```python
# test_auth.py
from agents.AuthenticationAgent import AuthenticationAgent

auth = AuthenticationAgent()

# Test authentication
result = auth.authenticate("1231777770", "test123")
print(f"Authentication result: {result}")

# Test invalid credentials
result = auth.authenticate("1231777770", "wrongpassword")
print(f"Invalid auth result: {result}")

# Test get student info
student = auth.get_student_info("1231777770")
print(f"Student info: {student.name}, {student.email}")
```

---

## Step 4: Calendar Service Testing

After implementing Calendar Service, test with:

```python
# test_calendar.py
from services.CalendarService import CalendarService

calendar = CalendarService()

# Test slot generation
slots = calendar.generate_slots_for_advisor("cciemnoc@asu.edu", "2025-02-01")
print(f"Generated {len(slots)} slots for date")

# Test availability check
available = calendar.check_slot_availability("cciemnoc@asu.edu", slots[0])
print(f"Slot available: {available}")
```

---

## Step 5: Booking Agent Testing

After implementing Booking Agent, test with:

```python
# test_booking.py
from agents.BookingAgent import BookingAgent
from datetime import datetime

booking = BookingAgent()

# Test get available slots
slots = booking.get_available_slots("cciemnoc@asu.edu", "2025-02-01", "2025-02-07")
print(f"Available slots: {len(slots)}")

# Test book appointment
appointment = booking.book_appointment(
    student_id="1231777770",
    advisor_id="cciemnoc@asu.edu",
    slot_datetime=slots[0]
)
print(f"Appointment booked: {appointment.appointment_id}")
```

---

## Step 6: Email Service Testing

After implementing Email Service, test with:

```python
# test_email.py
from services.EmailService import EmailService

email = EmailService()

# Test send confirmation (requires SMTP config in .env)
result = email.send_appointment_confirmation(appointment)
print(f"Email sent: {result}")
```

**Note:** Requires SMTP credentials in `.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## Step 7: Intent Classifier Testing

After implementing Intent Classifier, test with:

```python
# test_intent.py
from agents.IntentClassifier import IntentClassifier

classifier = IntentClassifier()

# Test intent detection
intent = classifier.detect_intent("I want to book an appointment")
print(f"Intent: {intent}")  # Should be "booking"

intent = classifier.detect_intent("What are the graduation requirements?")
print(f"Intent: {intent}")  # Should be "question"
```

---

## Step 8: Agent Controller Testing

After implementing Agent Controller, test with:

```python
# test_controller.py
from agents.AgentController import AgentController

controller = AgentController()

# Test routing
result = controller.route_request("book appointment", {"student_id": "1231777770"})
print(f"Route result: {result}")
```

---

## Step 9: UI Testing

After updating main.py, test with:

```bash
streamlit run main.py
```

**Test scenarios:**
1. Open app → Should load RAG system
2. Type "book appointment" → Should trigger booking flow
3. Select program level → Should show appropriate advisors
4. Select advisor → Should show available slots
5. Select slot → Should book and show confirmation

---

## Quick Test Commands

```bash
# Test database
python database/test_db.py

# Test specific component (after implementation)
python test_auth.py
python test_calendar.py
python test_booking.py

# Run full app
streamlit run main.py
```

---

## Troubleshooting

### Database errors:
- Make sure you ran `python database/init_db.py` first
- Check that `database/appointments.db` exists
- Verify SQLAlchemy is installed: `pip install sqlalchemy`

### Import errors:
- Make sure you're running from project root directory
- Check that all `__init__.py` files exist in folders

### Missing dependencies:
- Run `pip install -r requirements.txt`
- Check that all packages are installed: `pip list`


