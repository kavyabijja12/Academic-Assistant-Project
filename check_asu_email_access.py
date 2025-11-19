"""
Check ASU Email Access Options
This script helps determine what email access methods are available
"""

print("=" * 60)
print("ASU Email Access Check")
print("=" * 60)

print("\nASU email accounts are Office 365 accounts managed by ASU.")
print("They may have different access methods than personal Microsoft accounts.\n")

print("=" * 60)
print("Option 1: Office 365 App Passwords (Try This First)")
print("=" * 60)
print("1. Go to: https://account.activedirectory.windowsazure.com/AppPasswords.aspx")
print("2. Sign in with: kbijja@asu.edu")
print("3. If page loads, click 'Create' to generate App Password")
print("4. Copy the password and add to .env file")

print("\n" + "=" * 60)
print("Option 2: ASU Office 365 Portal")
print("=" * 60)
print("1. Go to: https://outlook.office.com")
print("2. Sign in with: kbijja@asu.edu")
print("3. Click your profile → 'My account' → 'Security'")
print("4. Look for 'App passwords' or 'Advanced security'")

print("\n" + "=" * 60)
print("Option 3: Contact ASU IT")
print("=" * 60)
print("If App Passwords are not available:")
print("- Email: itsupport@asu.edu")
print("- Phone: 480-965-6500")
print("- Ask: 'How do I get an App Password for SMTP email access?'")
print("- Or: 'What are the SMTP settings for ASU email?'")

print("\n" + "=" * 60)
print("Option 4: Alternative SMTP Servers to Try")
print("=" * 60)
print("Once you have an App Password, try these in .env:")
print("\nFor Outlook/Office 365:")
print("  SMTP_HOST=smtp-mail.outlook.com")
print("  SMTP_PORT=587")
print("\nFor ASU-specific:")
print("  SMTP_HOST=smtp.asu.edu")
print("  SMTP_PORT=587")
print("\nOr:")
print("  SMTP_HOST=outlook.office365.com")
print("  SMTP_PORT=587")

print("\n" + "=" * 60)
print("Option 5: Skip Email for Now")
print("=" * 60)
print("You can continue building the app without email:")
print("- Booking system will work")
print("- Appointments will be saved in database")
print("- Just won't send confirmation emails")
print("- Can add email later when you get App Password")

print("\n" + "=" * 60)
print("Next Steps")
print("=" * 60)
print("1. Try Option 1 first (Office 365 App Passwords)")
print("2. If that doesn't work, try Option 2 (Office 365 Portal)")
print("3. If still not available, contact ASU IT (Option 3)")
print("4. Or continue building app and add email later (Option 5)")

print("\n" + "=" * 60)


