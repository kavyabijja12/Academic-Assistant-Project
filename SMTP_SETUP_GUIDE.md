# ASU Email SMTP Setup Guide

## Quick Steps to Get App Password

### Step 1: Go to Microsoft Account Security
1. Open: **https://myaccount.microsoft.com/security**
2. Sign in with: `kbijja@asu.edu` and your ASU password
3. If prompted for 2FA, complete it

### Step 2: Find App Passwords
- Look for **"App passwords"** in the Security page
- If you don't see it, try: **https://account.microsoft.com/security/app-passwords**
- Or click: **"Advanced security options"** → **"App passwords"**

### Step 3: Create App Password
1. Click **"Create a new app password"** or **"Add"**
2. Name it: **"Academic Assistant"** or **"ASU Academic Assistant"**
3. Click **"Generate"** or **"Create"**
4. **IMPORTANT**: Copy the password immediately (you can't see it again!)
   - Format: `xxxx-xxxx-xxxx-xxxx` (16 characters with dashes)
   - Or: `xxxxxxxxxxxxxxxx` (16 characters without dashes)

### Step 4: Add to .env File
Open your `.env` file and add:

```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=kbijja@asu.edu
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

Replace `xxxx-xxxx-xxxx-xxxx` with the App Password you copied.

### Step 5: Test Configuration
Run the test script:
```bash
python test_smtp_config.py
```

This will try different SMTP servers and tell you which one works.

---

## Alternative: If App Passwords Not Available

If you can't find App Passwords in your Microsoft account:

### Option 1: Contact ASU IT
- Email: **itsupport@asu.edu**
- Phone: **480-965-6500**
- Ask: "How do I get an App Password for SMTP email access?"

### Option 2: Check ASU Email Settings
- Go to: **https://outlook.office.com**
- Sign in with ASU credentials
- Check email settings for SMTP configuration

### Option 3: Use ASU IT Documentation
- Search: "ASU email SMTP settings" or "ASU email app password"
- Check ASU IT knowledge base

---

## Common Issues

### Issue: "App passwords" option not visible
**Solution**: 
- Make sure 2-Step Verification is enabled
- Try accessing directly: https://account.microsoft.com/security/app-passwords
- Use a different browser or incognito mode

### Issue: "Authentication failed"
**Solution**:
- Make sure you're using App Password, NOT your regular password
- Check if password has spaces (remove them)
- Verify the password was copied correctly

### Issue: "Connection refused"
**Solution**:
- Try different SMTP servers (use test_smtp_config.py)
- Check if your network blocks port 587
- Try port 465 instead

---

## Testing

After adding credentials to `.env`, test with:

```bash
# Test SMTP configuration
python test_smtp_config.py

# Test email service
python test_email.py
```

---

## Security Note

⚠️ **Never commit your `.env` file to git!**
- The `.env` file should be in `.gitignore`
- App Passwords are sensitive - keep them secret
- If exposed, revoke the App Password and create a new one


