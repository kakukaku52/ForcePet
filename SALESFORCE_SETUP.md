# Salesforce Connected App Setup Guide

## Overview
To use OAuth login with Salesforce, you need to create a Connected App in your Salesforce organization. This guide will walk you through the process.

## Step 1: Create a Connected App in Salesforce

1. **Login to Salesforce**
   - Go to your Salesforce org (either Production or Sandbox)
   - Navigate to Setup

2. **Create the Connected App**
   - In Setup, search for "App Manager" in the Quick Find box
   - Click on **App Manager**
   - Click **New Connected App** button

3. **Configure Basic Information**
   - **Connected App Name**: Django Workbench (or your preferred name)
   - **API Name**: Django_Workbench (auto-populated)
   - **Contact Email**: Your email address

4. **Configure OAuth Settings**
   - Check **Enable OAuth Settings**
   - **Callback URL**:
     - For local development: `http://localhost:8002/auth/callback/`
     - For production: `https://yourdomain.com/auth/callback/`
   - **Selected OAuth Scopes**: Move these scopes to Selected:
     - Access and manage your data (api)
     - Perform requests on your behalf at any time (refresh_token, offline_access)
     - Provide access to your data via the Web (web)
     - Full access (full)

5. **Additional Settings**
   - Check **Require Secret for Web Server Flow**
   - Check **Require Secret for Refresh Token Flow**
   - Leave other settings as default

6. **Save the Connected App**
   - Click **Save**
   - Click **Continue**

## Step 2: Get Your OAuth Credentials

After saving, you'll need to retrieve your credentials:

1. **View the Connected App**
   - After saving, click on **Manage Consumer Details**
   - You may need to verify your identity

2. **Copy the Credentials**
   - **Consumer Key**: Copy this value
   - **Consumer Secret**: Click to reveal and copy this value

## Step 3: Update Your .env File

Update your `.env` file with the actual values:

```env
# Salesforce Configuration
SALESFORCE_CONSUMER_KEY=YOUR_ACTUAL_CONSUMER_KEY_HERE
SALESFORCE_CONSUMER_SECRET=YOUR_ACTUAL_CONSUMER_SECRET_HERE
SALESFORCE_REDIRECT_URI=http://localhost:8002/auth/callback/
SALESFORCE_API_VERSION=62.0
```

**Important**:
- Replace `YOUR_ACTUAL_CONSUMER_KEY_HERE` with your actual Consumer Key
- Replace `YOUR_ACTUAL_CONSUMER_SECRET_HERE` with your actual Consumer Secret
- Make sure the redirect URI matches exactly (including the port 8002)

## Step 4: Configure IP Restrictions (Optional but Recommended)

For development:
1. In the Connected App settings, go to **Manage**
2. Click **Edit Policies**
3. Under **IP Relaxation**, select **Relax IP restrictions**
4. Click **Save**

For production:
1. Keep **Enforce IP restrictions**
2. Add your server's IP addresses to the trusted IP ranges

## Step 5: Test the Configuration

1. Restart your Django server to load the new environment variables:
   ```bash
   # Stop the server (Ctrl+C) and restart
   python3 manage.py runserver 8002
   ```

2. Go to http://localhost:8002/auth/login/
3. Click on the **OAuth Login** tab
4. Select your environment (Production or Sandbox)
5. Click **Login with Salesforce**

## Troubleshooting

### Error: invalid_client_id
- **Cause**: The Consumer Key is not valid or not properly configured
- **Solution**:
  - Verify you copied the Consumer Key correctly
  - Check that there are no extra spaces or characters
  - Ensure the Connected App is active in Salesforce

### Error: redirect_uri_mismatch
- **Cause**: The callback URL doesn't match what's configured in Salesforce
- **Solution**:
  - Ensure the callback URL in Salesforce exactly matches your .env file
  - Include the correct port number (8002)
  - Don't forget the trailing slash

### Error: invalid_client
- **Cause**: The Consumer Secret is incorrect
- **Solution**:
  - Re-copy the Consumer Secret from Salesforce
  - Make sure you clicked "Reveal" to see the actual secret

### Can't see Consumer Secret
- Go to **App Manager** → Find your app → **View**
- Click **Manage Consumer Details**
- Verify your identity if prompted
- The Consumer Secret will be displayed

## Security Best Practices

1. **Never commit your .env file to version control**
   - Add `.env` to your `.gitignore` file

2. **Use different Connected Apps for different environments**
   - Create separate apps for Development, Staging, and Production

3. **Rotate your Consumer Secret regularly**
   - You can regenerate the secret in the Connected App settings

4. **Use HTTPS in production**
   - Update your callback URL to use HTTPS
   - Update SALESFORCE_REDIRECT_URI accordingly

## Alternative: Username/Password Login

If you prefer not to use OAuth, you can use the **Username/Password** tab on the login page. This requires:
- Your Salesforce username
- Your Salesforce password
- Your security token (append it to your password)

To get your security token:
1. In Salesforce, go to your personal settings
2. Search for "Reset My Security Token"
3. Click **Reset Security Token**
4. Check your email for the new token