# Quick Start Guide

## First Time Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize database:**
   ```bash
   python database/init_db.py
   ```

3. **Run the app:**
   ```bash
   streamlit run main.py
   ```

## If You Get Import Errors

If you see `ModuleNotFoundError`:

1. **Install missing packages:**
   ```bash
   pip install bcrypt sqlalchemy email-validator python-dateutil
   ```

2. **Or install all requirements:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Restart Streamlit** (stop with Ctrl+C, then run again)

## Test Login

- **ASU ID:** `1231777770`
- **Password:** `test123`

## Using the App

1. **Ask Questions:** Type any question in the chat
2. **Book Appointment:** 
   - Click "Book Appointment" button (sidebar or main area)
   - OR type "book appointment" in chat
   - Follow the 4-step flow

## Troubleshooting

- **Import errors:** Make sure all packages are installed in the same Python environment Streamlit uses
- **Database errors:** Run `python database/init_db.py` first
- **Email not working:** That's okay - booking still works, just no confirmation emails


