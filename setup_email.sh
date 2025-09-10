#!/bin/bash

# Email Setup Script for Railway
# This script helps you set up email credentials for the password reset feature

echo "==================================="
echo "Email Configuration Setup for Railway"
echo "==================================="
echo ""
echo "To use the password reset feature, you need to configure email settings."
echo ""
echo "For Gmail users:"
echo "1. Enable 2-Factor Authentication on your Google account"
echo "2. Generate an App Password at: https://myaccount.google.com/apppasswords"
echo "3. Use the App Password (not your regular password) below"
echo ""

read -p "Enter your Gmail address (e.g., yourname@gmail.com): " email
read -s -p "Enter your Gmail App Password (will be hidden): " password
echo ""

# Set the email credentials in Railway
railway variables --set "MAIL_USERNAME=$email" --set "MAIL_PASSWORD=$password" --set "MAIL_DEFAULT_SENDER=$email"

echo ""
echo "✅ Email credentials have been set on Railway!"
echo ""
echo "The app will now redeploy automatically with the new settings."
echo "Password reset emails will be sent from: $email"
echo ""
echo "You can test the feature by:"
echo "1. Going to your app's login page"
echo "2. Clicking 'Forgot your password?'"
echo "3. Entering an email address to receive the reset link"
