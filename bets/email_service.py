from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_verification_email(user_email, verification_token, username):
    """
    Send email verification link to user
    """
    subject = 'Verify your FriendlyBet account'

    # For now, using a simple HTML template
    # You can customize this URL based on your frontend routing
    verification_url = f"{settings.CORS_ALLOWED_ORIGINS[0]}/verify-email?token={verification_token}"

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50; text-align: center;">Welcome to FriendlyBet!</h2>
                <p style="color: #555; font-size: 16px;">Hi {username},</p>
                <p style="color: #555; font-size: 16px;">
                    Thank you for registering! Please verify your email address by clicking the button below:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                <p style="color: #777; font-size: 14px;">
                    Or copy and paste this link in your browser:<br>
                    <a href="{verification_url}" style="color: #3498db;">{verification_url}</a>
                </p>
                <p style="color: #777; font-size: 14px; margin-top: 30px;">
                    This link will expire in 24 hours.
                </p>
                <p style="color: #777; font-size: 14px;">
                    If you didn't create an account, please ignore this email.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    FriendlyBet - Sports Betting & Predictions
                </p>
            </div>
        </body>
    </html>
    """

    plain_message = strip_tags(html_message)

    try:
        logger.info(f"Sending verification email to {user_email}")
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Verification email sent successfully to {user_email}. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send verification email to {user_email}: {str(e)}")
        raise


def send_password_reset_email(user_email, reset_token, username):
    """
    Send password reset link to user
    """
    subject = 'Reset your FriendlyBet password'

    # Password reset URL
    reset_url = f"{settings.CORS_ALLOWED_ORIGINS[0]}/reset-password?token={reset_token}"

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50; text-align: center;">Password Reset Request</h2>
                <p style="color: #555; font-size: 16px;">Hi {username},</p>
                <p style="color: #555; font-size: 16px;">
                    We received a request to reset your password. Click the button below to create a new password:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #777; font-size: 14px;">
                    Or copy and paste this link in your browser:<br>
                    <a href="{reset_url}" style="color: #e74c3c;">{reset_url}</a>
                </p>
                <p style="color: #777; font-size: 14px; margin-top: 30px;">
                    This link will expire in 1 hour.
                </p>
                <p style="color: #e74c3c; font-size: 14px; font-weight: bold;">
                    If you didn't request a password reset, please ignore this email and your password will remain unchanged.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    FriendlyBet - Sports Betting & Predictions
                </p>
            </div>
        </body>
    </html>
    """

    plain_message = strip_tags(html_message)

    try:
        logger.info(f"Sending password reset email to {user_email}")
        logger.info(f"Reset URL: {reset_url}")
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password reset email sent successfully to {user_email}. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")
        raise
