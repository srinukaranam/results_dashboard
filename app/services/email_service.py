"""Email service for sending OTP and notifications."""

import random
import string
from datetime import datetime, timedelta
from flask import current_app, render_template
from flask_mail import Mail, Message
from app.extensions import db

mail = Mail()


def init_mail(app):
    """Initialize Flask-Mail with app."""
    mail.init_app(app)


def generate_otp(length=6):
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def send_otp_email(student):
    """Send OTP verification email to student.

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Generate OTP
        otp = generate_otp()

        # Store OTP in database
        student.otp_code = otp
        student.otp_expiry = datetime.utcnow() + timedelta(
            minutes=current_app.config["OTP_EXPIRY_MINUTES"]
        )
        student.otp_attempts = 0
        db.session.commit()

        # Create email
        subject = f"Verify Your Email - Result Dashboard | OTP: {otp}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="background: #0F1923; padding: 20px; border-radius: 8px; text-align: center;">
                    <h1 style="color: #00D4FF; font-family: 'Courier New', monospace; margin: 0;">◈ Result Dashboard</h1>
                    <p style="color: #8B949E; font-size: 12px; margin: 5px 0;">JNTUK-Affiliated College</p>
                </div>
                
                <h2 style="color: #0F172A; margin-top: 25px;">Hello {student.first_name},</h2>
                <p style="color: #475569; line-height: 1.6;">Thank you for registering with Result Dashboard. Please verify your email address using the OTP below:</p>
                
                <div style="background: #F8FAFC; border: 2px dashed #00D4FF; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                    <p style="color: #64748B; font-size: 12px; margin: 0;">Your One-Time Password</p>
                    <h1 style="color: #0F172A; font-family: 'Courier New', monospace; font-size: 36px; letter-spacing: 8px; margin: 10px 0;">{otp}</h1>
                    <p style="color: #64748B; font-size: 11px; margin: 0;">Expires in {current_app.config['OTP_EXPIRY_MINUTES']} minutes</p>
                </div>
                
                <p style="color: #94A3B8; font-size: 12px; text-align: center;">
                    If you did not request this, please ignore this email.<br>
                    &copy; 2024 Result Dashboard System
                </p>
            </div>
        </body>
        </html>
        """

        msg = Message(subject=subject, recipients=[student.email], html=html_body)

        mail.send(msg)
        return True, "OTP sent successfully! Check your email."

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Email send failed: {str(e)}")
        return False, f"Failed to send email: {str(e)}"


def resend_otp(student):
    """Resend OTP to student."""
    # Check if previous OTP exists and is still valid
    if student.is_verified:
        return False, "Email is already verified."

    # Fix: Handle None value
    attempts = student.otp_attempts if student.otp_attempts is not None else 0
    if attempts >= 5:
        return False, "Too many attempts. Please contact admin."

    return send_otp_email(student)


def verify_otp(student, otp_input):
    """Verify the OTP entered by student."""
    if student.is_verified:
        return True, "Email already verified."

    if not student.otp_code:
        return False, "No OTP found. Please request a new one."

    if student.otp_expiry and student.otp_expiry < datetime.utcnow():
        student.otp_code = None
        student.otp_expiry = None
        db.session.commit()
        return False, "OTP has expired. Please request a new one."

    # Fix: Handle None value
    attempts = student.otp_attempts if student.otp_attempts is not None else 0
    if attempts >= 5:
        student.otp_code = None
        db.session.commit()
        return False, "Too many failed attempts. Please request a new OTP."

    if student.otp_code != otp_input:
        student.otp_attempts = attempts + 1
        db.session.commit()
        remaining = 5 - student.otp_attempts
        return False, f"Invalid OTP. {remaining} attempts remaining."

    # OTP verified successfully
    student.is_verified = True
    student.otp_code = None
    student.otp_expiry = None
    student.otp_attempts = 0
    db.session.commit()

    return True, "Email verified successfully!"
