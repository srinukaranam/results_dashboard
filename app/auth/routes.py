from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models import Student, AuditLog, Admin
from app.auth.forms import RegistrationForm, LoginForm
from app.services.email_service import send_otp_email, resend_otp, verify_otp
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
import json

auth_bp = Blueprint("auth", __name__)


def log_audit_event(actor_type, actor_id, event_type, extra_data=None):
    if isinstance(extra_data, dict):
        extra_data = json.dumps(extra_data)
    log = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        ip_address=request.remote_addr,
        extra_data=extra_data,
    )
    db.session.add(log)
    db.session.commit()


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if current_user.is_authenticated:
        if isinstance(current_user, Student):
            return redirect(url_for("student.dashboard"))
        else:
            return redirect(url_for("admin.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        student = Student(
            hall_ticket=form.hall_ticket.data.upper(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data.lower(),
            username=form.username.data.lower() if form.username.data else None,
            branch=form.branch.data,
            admission_year=form.admission_year.data,
            is_verified=False,
        )
        student.set_password(form.password.data)

        # Handle profile photo
        if form.profile_photo.data:
            filename = secure_filename(
                f"{student.hall_ticket}_{form.profile_photo.data.filename}"
            )
            upload_path = os.path.join("app/static/uploads/profiles", filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            form.profile_photo.data.save(upload_path)
            student.profile_photo = filename

        db.session.add(student)
        db.session.commit()

        # Send OTP
        success, message = send_otp_email(student)

        log_audit_event("student", student.id, "REGISTER", {"email": student.email})

        if success:
            flash("Registration successful! Please verify your email.", "success")
            # Store student ID in session for OTP verification
            session["pending_verification_id"] = student.id
            return redirect(url_for("auth.verify_email"))
        else:
            flash(f"Registration successful but email failed: {message}", "warning")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    """OTP verification page."""
    student_id = session.get("pending_verification_id")

    if not student_id:
        flash("No pending verification found. Please login or register.", "warning")
        return redirect(url_for("auth.login"))

    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("auth.register"))

    if student.is_verified:
        flash("Email already verified! You can login now.", "success")
        session.pop("pending_verification_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        otp_input = request.form.get("otp", "").strip()

        if len(otp_input) != 6 or not otp_input.isdigit():
            flash("Please enter a valid 6-digit OTP.", "warning")
        else:
            success, message = verify_otp(student, otp_input)

            if success:
                log_audit_event("student", student.id, "EMAIL_VERIFIED")
                session.pop("pending_verification_id", None)
                flash(message, "success")
                return redirect(url_for("auth.login"))
            else:
                flash(message, "danger")

    return render_template("auth/verify_email.html", student=student)


@auth_bp.route("/resend-otp")
def resend_otp_route():
    """Resend OTP."""
    student_id = session.get("pending_verification_id")

    if not student_id:
        flash("No pending verification found.", "warning")
        return redirect(url_for("auth.login"))

    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("auth.register"))

    if student.is_verified:
        flash("Email already verified!", "success")
        session.pop("pending_verification_id", None)
        return redirect(url_for("auth.login"))

    success, message = resend_otp(student)

    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for("auth.verify_email"))


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        if isinstance(current_user, Student):
            return redirect(url_for("student.dashboard"))
        else:
            return redirect(url_for("admin.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        login_id = form.login_id.data.lower()

        student = Student.query.filter(
            (Student.email == login_id) | (Student.username == login_id)
        ).first()

        if student:
            if student.is_locked():
                flash("Account temporarily locked. Try again later.", "danger")
                log_audit_event("student", student.id, "LOGIN_ATTEMPT_LOCKED")
                return render_template("auth/login.html", form=form)

            if student.check_password(form.password.data):
                # Check if email is verified
                if not student.is_verified:
                    flash("Please verify your email before logging in.", "warning")
                    session["pending_verification_id"] = student.id
                    return redirect(url_for("auth.verify_email"))

                student.reset_failed_attempts()
                student.last_login = datetime.utcnow()
                db.session.commit()

                login_user(student, remember=True)
                session.permanent = True

                log_audit_event("student", student.id, "LOGIN_SUCCESS")
                flash(f"Welcome back, {student.first_name}!", "success")

                next_page = request.args.get("next")
                if next_page:
                    return redirect(next_page)
                return redirect(url_for("student.dashboard"))
            else:
                student.increment_failed_attempts()
                db.session.commit()
                log_audit_event(
                    "student", student.id, "LOGIN_FAILED", {"reason": "wrong_password"}
                )
                flash("Invalid login credentials.", "danger")
        else:
            flash("Invalid login credentials.", "danger")
            log_audit_event(
                "student",
                None,
                "LOGIN_FAILED",
                {"login_id": login_id, "reason": "not_found"},
            )

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    if isinstance(current_user, Student):
        log_audit_event("student", current_user.id, "LOGOUT")
    elif isinstance(current_user, Admin):
        log_audit_event("admin", current_user.id, "LOGOUT")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("landing"))
