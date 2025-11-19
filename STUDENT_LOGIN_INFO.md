# Student Login Credentials

## Main Test Student (Created by init_db.py)

**ASU ID:** `1231777770`  
**Password:** `test123`  
**Name:** Kavya Bijja  
**Email:** kbijja@asu.edu  
**Program:** Undergraduate  

**✅ This is the main test account you should use for testing!**

---

## Other Test Students

The following students were created by test scripts and may have random passwords. They are not recommended for login testing:

- **ASU ID:** 9998887777 (Test Student - undergraduate)
- **ASU ID:** 8887776666 (Password Test - graduate)  
- **ASU ID:** 999468973 (Test Student - undergraduate)
- **ASU ID:** 999576549 (Test Student - undergraduate)
- **ASU ID:** 888618227 (Password Test - graduate)

---

## How to Test Login

1. **Start the app:**
   ```bash
   streamlit run main.py
   ```

2. **Click "Book Appointment" button** or type "book appointment" in chat

3. **Login with:**
   - ASU ID: `1231777770`
   - Password: `test123`

4. **You should see:**
   - Authentication successful message
   - Program selection (Undergraduate/Graduate)
   - Advisor selection (filtered by program)
   - Time slot selection
   - Booking confirmation

---

## Create New Test Student (Optional)

If you want to create additional test students, you can use the AuthenticationAgent:

```python
from agents.AuthenticationAgent import AuthenticationAgent

auth = AuthenticationAgent()
result = auth.create_student(
    asu_id="1234567890",
    email="newstudent@asu.edu",
    name="New Student",
    password="mypassword",
    program_level="undergraduate"
)
```


