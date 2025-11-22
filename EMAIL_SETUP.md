# Email Configuration Guide for GlobalDesignerHub

## Overview
This guide will help you configure email settings so users can receive password reset notifications and other system emails.

## Development Mode
In development (DEBUG=True), if no email credentials are provided, emails will print to the console instead of sending. This is useful for testing without setting up SMTP.

## Production Setup

### Option 1: Gmail (Recommended for Small Projects)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Create an App Password**:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Copy the 16-character password

3. **Add to `.env` file**:
```env
EMAIL_HOST_USER=your.email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=GlobalDesignerHub <your.email@gmail.com>
```

### Option 2: SendGrid (Recommended for Production)

1. **Sign up at SendGrid.com** (free tier: 100 emails/day)
2. **Create an API key**
3. **Add to `.env` file**:
```env
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=GlobalDesignerHub <no-reply@globaldesignerhub.com>
```

### Option 3: Mailgun

```env
EMAIL_HOST_USER=postmaster@your-domain.mailgun.org
EMAIL_HOST_PASSWORD=your-mailgun-smtp-password
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=GlobalDesignerHub <no-reply@your-domain.com>
```

### Option 4: Amazon SES

```env
EMAIL_HOST_USER=your-ses-smtp-username
EMAIL_HOST_PASSWORD=your-ses-smtp-password
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=GlobalDesignerHub <no-reply@your-domain.com>
```

### Option 5: Office365/Outlook

```env
EMAIL_HOST_USER=your.email@outlook.com
EMAIL_HOST_PASSWORD=your-password
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=GlobalDesignerHub <your.email@outlook.com>
```

## Testing Email Configuration

Run this command to test your email setup:

```bash
python manage.py test_email recipient@example.com
```

This will:
- Show your current email backend configuration
- Attempt to send a test email
- Display any errors if sending fails
- Provide troubleshooting tips

## Troubleshooting

### Gmail: "Username and Password not accepted"
- Use App Password, not your regular Gmail password
- Enable 2-Factor Authentication first
- Check that "Less secure app access" is NOT needed (App Passwords work without it)

### SendGrid: Authentication Failed
- Make sure you use `apikey` as the username (literally)
- Double-check your API key
- Verify the API key has "Mail Send" permissions

### General Issues

**Timeout errors:**
- Check firewall settings allow outgoing connections on SMTP port (587 or 465)
- Verify EMAIL_HOST and EMAIL_PORT are correct
- Try increasing EMAIL_TIMEOUT in settings

**SSL/TLS errors:**
- For port 587: Use EMAIL_USE_TLS=True, EMAIL_USE_SSL=False
- For port 465: Use EMAIL_USE_SSL=True, EMAIL_USE_TLS=False

**Emails go to spam:**
- Set up SPF, DKIM, and DMARC records for your domain
- Use a reputable email service (SendGrid, Mailgun, SES)
- Include unsubscribe links in emails
- Use a consistent FROM address

## Password Reset Flow

1. User clicks "Forgot Password?" on login page
2. User enters their email or username
3. System sends password reset email (if account exists)
4. User clicks link in email
5. User sets new password
6. User is redirected to login page

**Security Features:**
- Reset links expire after 24 hours
- Each link can only be used once
- System doesn't reveal if email exists (for security)

## Custom Email Templates

Email templates are located in:
```
designer_portfolio/templates/registration/
├── password_reset_email.html      # HTML email body
├── password_reset_subject.txt     # Email subject line
├── password_reset_form.html       # Request reset form
├── password_reset_done.html       # Confirmation page
├── password_reset_confirm.html    # New password form
└── password_reset_complete.html   # Success page
```

## Production Checklist

- [ ] Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
- [ ] Configure correct EMAIL_HOST and EMAIL_PORT
- [ ] Set DEFAULT_FROM_EMAIL to your domain
- [ ] Test email sending with `python manage.py test_email`
- [ ] Verify emails don't go to spam
- [ ] Set up SPF/DKIM records for your domain
- [ ] Monitor email sending in production
- [ ] Set up email error notifications

## Support

For issues with email configuration:
1. Check the console/logs for error messages
2. Run the test_email command
3. Verify environment variables are loaded correctly
4. Check your email provider's documentation
5. Contact your hosting provider if firewall issues occur

## Additional Resources

- [Django Email Documentation](https://docs.djangoproject.com/en/stable/topics/email/)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [SendGrid SMTP](https://docs.sendgrid.com/for-developers/sending-email/integrating-with-the-smtp-api)
- [Mailgun SMTP](https://documentation.mailgun.com/en/latest/user_manual.html#sending-via-smtp)
