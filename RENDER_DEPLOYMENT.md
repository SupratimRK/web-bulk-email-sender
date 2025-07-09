# Render Deployment Guide

## Prerequisites
1. GitHub account
2. Render account (free tier available)
3. Your email provider credentials

## Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit with Render deployment files"
git branch -M main
git remote add origin https://github.com/yourusername/bulk-mailer-app.git
git push -u origin main
```

## Step 2: Deploy to Render

### Option A: Using render.yaml (Recommended)
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Blueprint"
3. Connect your GitHub repository
4. Select the repository with your bulk mailer app
5. Render will automatically detect the `render.yaml` file
6. Click "Apply"

### Option B: Manual Web Service Creation
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: bulk-mailer-app
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
   - **Plan**: Free

## Step 3: Configure Environment Variables

In your Render service settings, add these environment variables:

### Required Variables:
- `SENDER_EMAIL`: Your email address (used for SMTP login/authentication)
- `PASSWORD`: Your email app password
- `FLASK_SECRET_KEY`: A random secret key for Flask sessions

### Optional Variables:
- `display_name`: Your sender display name
- `from_email`: Email address shown in 'From' header (defaults to sender_email)
- `MAILER_HOST`: SMTP host (default: smtp.gmail.com)
- `MAILER_PORT`: SMTP port (default: 587)
- `FLASK_ENV`: Set to "production"

### How to Set Environment Variables:
1. Go to your service in Render Dashboard
2. Click "Environment" tab
3. Add each variable with its value
4. Click "Save Changes"

## Step 4: Keep Your App Alive

The app includes an automatic keep-alive service that:
- Pings your app every 5 minutes
- Only runs in production mode
- Prevents Render's free tier from sleeping

### How it works:
- The `keep_alive.py` service automatically starts when deployed
- It uses the `RENDER_EXTERNAL_URL` environment variable (auto-set by Render)
- Sends HTTP requests to keep the app active

## Step 5: Email Provider Setup

### For Gmail:
1. Enable 2-Factor Authentication
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. Use your Gmail address for `SENDER_EMAIL` (login email)
4. Use the app password for `PASSWORD`
5. Optionally set `from_email` if you want a different display email

### For Other Providers:
- **MailerSend**: Default configuration works
- **SendGrid**: Use their SMTP settings
- **Custom SMTP**: Set `MAILER_HOST` and `MAILER_PORT`

## Step 6: Test Your Deployment

1. Visit your Render app URL
2. Create a test CSV with email headers
3. Send a test email to yourself
4. Check the logs in Render Dashboard for any issues

## Troubleshooting

### Common Issues:

1. **App not staying alive**:
   - Check that `FLASK_ENV=production` is set
   - Verify `RENDER_EXTERNAL_URL` is available
   - Check logs for keep-alive service messages

2. **Email sending fails**:
   - Verify email credentials
   - Check SMTP settings
   - Review firewall/security settings

3. **Build fails**:
   - Check requirements.txt syntax
   - Verify Python version compatibility

### Viewing Logs:
1. Go to Render Dashboard
2. Select your service
3. Click "Logs" tab
4. Monitor real-time logs

## Free Tier Limitations

Render Free Tier includes:
- 750 hours/month of runtime
- Apps sleep after 15 minutes of inactivity
- Limited bandwidth and storage

The keep-alive service helps maximize uptime within the free tier limits.

## Production Recommendations

For production use, consider:
1. Upgrading to Render's paid plans for better reliability
2. Using a dedicated email service (SendGrid, MailerSend)
3. Implementing rate limiting for bulk emails
4. Adding email analytics and tracking
5. Using a database for storing sending history

## Security Notes

- Never commit `.env` files to Git
- Use environment variables for all sensitive data
- Regularly rotate email passwords
- Monitor sending logs for suspicious activity

## Support

- Render Documentation: https://render.com/docs
- Flask Documentation: https://flask.palletsprojects.com/
- Issues: Check your GitHub repository issues
