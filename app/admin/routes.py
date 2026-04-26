from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
    current_app,
)  # Added current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models import Admin, Student, PDFUpload, AuditLog, Result, Notification
from app.auth.forms import AdminLoginForm
from app.admin.forms import PDFUploadForm
from app.services.pdf_parser import parse_jntuk_pdf, compute_file_hash
from datetime import datetime, timedelta
import json
import os
from werkzeug.utils import secure_filename

admin_bp = Blueprint("admin", __name__)


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


@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for("admin.dashboard"))
        else:
            return redirect(url_for("student.dashboard"))

    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(email=form.email.data.lower()).first()

        if admin:
            if admin.is_locked():
                flash("Account temporarily locked. Try again later.", "danger")
                log_audit_event("admin", admin.id, "LOGIN_ATTEMPT_LOCKED")
                return render_template("admin/login.html", form=form)

            if admin.check_password(form.password.data):
                admin.reset_failed_attempts()
                admin.last_login = datetime.utcnow()
                db.session.commit()

                login_user(admin, remember=True)
                session.permanent = True

                log_audit_event("admin", admin.id, "LOGIN_SUCCESS")
                flash("Admin login successful.", "success")
                return redirect(url_for("admin.dashboard"))
            else:
                admin.increment_failed_attempts()
                db.session.commit()
                log_audit_event("admin", admin.id, "LOGIN_FAILED")
                flash("Invalid credentials.", "danger")
        else:
            flash("Invalid credentials.", "danger")
            log_audit_event("admin", None, "LOGIN_FAILED", {"email": form.email.data})

    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout")
@login_required
def logout():
    if isinstance(current_user, Admin):
        log_audit_event("admin", current_user.id, "LOGOUT")
    logout_user()
    flash("Admin logged out.", "info")
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if not isinstance(current_user, Admin):
        flash("Access denied.", "danger")
        return redirect(url_for("landing"))

    form = PDFUploadForm()

    total_students = Student.query.count()
    total_uploads = PDFUpload.query.count()
    latest_upload = PDFUpload.query.order_by(PDFUpload.uploaded_at.desc()).first()

    recent_uploads = (
        PDFUpload.query.order_by(PDFUpload.uploaded_at.desc()).limit(10).all()
    )

    return render_template(
        "admin/dashboard.html",
        form=form,
        total_students=total_students,
        total_uploads=total_uploads,
        latest_upload=latest_upload,
        recent_uploads=recent_uploads,
    )


@admin_bp.route("/upload", methods=["POST"])
@login_required
def upload_pdf():
    if not isinstance(current_user, Admin):
        flash("Access denied.", "danger")
        return redirect(url_for("landing"))

    form = PDFUploadForm()

    if form.validate_on_submit():
        file = form.pdf_file.data
        semester = form.semester.data

        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(
            current_app.config["UPLOAD_FOLDER"], filename
        )  # Now works
        file.save(filepath)

        # Compute hash
        file_hash = compute_file_hash(filepath)

        # Create upload record
        upload = PDFUpload(
            admin_id=current_user.id,
            filename=filename,
            file_hash=file_hash,
            status="processing",
        )
        db.session.add(upload)
        db.session.commit()

        try:
            # Parse PDF
            result = parse_jntuk_pdf(filepath, current_user.id, filename, semester)

            # Update upload record
            upload.total_rows = result["total_rows"]
            upload.success_count = result["success_count"]
            upload.error_count = result["error_count"]
            upload.status = "done" if result["error_count"] == 0 else "done_with_errors"
            db.session.commit()

            log_audit_event(
                "admin",
                current_user.id,
                "PDF_PARSE_SUCCESS",
                {
                    "filename": filename,
                    "total": result["total_rows"],
                    "success": result["success_count"],
                    "errors": result["error_count"],
                },
            )

            flash(
                f'PDF parsed! {result["success_count"]} results stored, {result["error_count"]} errors.',
                "success",
            )

        except Exception as e:
            upload.status = "failed"
            db.session.commit()

            log_audit_event(
                "admin",
                current_user.id,
                "PDF_PARSE_FAILED",
                {"filename": filename, "error": str(e)},
            )

            flash(f"Parse failed: {str(e)}", "danger")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/uploads")
@login_required
def view_uploads():
    """View all uploads with details."""
    if not isinstance(current_user, Admin):
        return redirect(url_for("landing"))

    uploads = PDFUpload.query.order_by(PDFUpload.uploaded_at.desc()).all()

    return render_template("admin/uploads.html", uploads=uploads)


@admin_bp.route("/uploads/<int:upload_id>/delete", methods=["POST"])
@login_required
def delete_upload(upload_id):
    """Delete an upload and its associated results."""
    if not isinstance(current_user, Admin):
        flash("Access denied.", "danger")
        return redirect(url_for("landing"))

    upload = db.session.get(PDFUpload, upload_id)

    if not upload:
        flash("Upload not found.", "danger")
        return redirect(url_for("admin.view_uploads"))

    filename = upload.filename

    # Delete associated results
    Result.query.filter_by(pdf_source=filename).delete()

    # Delete associated notifications for this upload
    Notification.query.filter(Notification.message.like(f"%{filename}%")).delete()

    # Delete the PDF file
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    # Delete upload record
    db.session.delete(upload)
    db.session.commit()

    log_audit_event(
        "admin",
        current_user.id,
        "PDF_DELETED",
        {"filename": filename, "upload_id": upload_id},
    )

    flash(f'Upload "{filename}" and all its results deleted.', "success")
    return redirect(url_for("admin.view_uploads"))


@admin_bp.route("/uploads/<int:upload_id>/results")
@login_required
def view_upload_results(upload_id):
    """View results from a specific upload."""
    if not isinstance(current_user, Admin):
        return redirect(url_for("landing"))

    upload = db.session.get(PDFUpload, upload_id)
    if not upload:
        flash("Upload not found.", "danger")
        return redirect(url_for("admin.view_uploads"))

    results = Result.query.filter_by(pdf_source=upload.filename).limit(100).all()
    total = Result.query.filter_by(pdf_source=upload.filename).count()

    return render_template(
        "admin/upload_results.html", upload=upload, results=results, total=total
    )


@admin_bp.route("/students")
@login_required
def view_students():
    """View all registered students."""
    if not isinstance(current_user, Admin):
        return redirect(url_for("landing"))

    search = request.args.get("search", "")

    if search:
        students = (
            Student.query.filter(
                (Student.hall_ticket.contains(search))
                | (Student.first_name.contains(search))
                | (Student.last_name.contains(search))
                | (Student.email.contains(search))
            )
            .order_by(Student.created_at.desc())
            .all()
        )
    else:
        students = Student.query.order_by(Student.created_at.desc()).limit(50).all()

    total_students = Student.query.count()

    return render_template(
        "admin/students.html",
        students=students,
        total_students=total_students,
        search=search,
    )


@admin_bp.route("/audit-logs")
@login_required
def audit_logs():
    """View system audit logs."""
    if not isinstance(current_user, Admin):
        return redirect(url_for("landing"))

    page = request.args.get("page", 1, type=int)
    per_page = 50

    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page
    )

    return render_template("admin/audit_logs.html", logs=logs)


@admin_bp.route("/system-status")
@login_required
def system_status():
    """View system health status."""
    if not isinstance(current_user, Admin):
        return redirect(url_for("landing"))

    from app.extensions import db
    import os

    # REMOVE: import psutil  <-- Delete this line

    status = {
        "database": "connected",
        "total_students": Student.query.count(),
        "total_results": Result.query.count(),
        "total_uploads": PDFUpload.query.count(),
        "total_notifications": Notification.query.count(),
        "db_size": "N/A",
        "upload_folder_size": "N/A",
    }

    # Check database connection
    try:
        db.session.execute(db.text("SELECT 1"))
        status["database"] = "✅ Connected"
    except:
        status["database"] = "❌ Error"

    # Get upload folder size
    upload_path = current_app.config["UPLOAD_FOLDER"]
    if os.path.exists(upload_path):
        total_size = 0
        for f in os.listdir(upload_path):
            fp = os.path.join(upload_path, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
        status["upload_folder_size"] = f"{total_size / (1024*1024):.1f} MB"

    # Recent failed logins (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    status["recent_failed_logins"] = AuditLog.query.filter(
        AuditLog.event_type == "LOGIN_FAILED", AuditLog.created_at >= yesterday
    ).count()

    return render_template("admin/system_status.html", status=status)


@admin_bp.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    """Delete a student and all their data."""
    if not isinstance(current_user, Admin):
        flash("Access denied.", "danger")
        return redirect(url_for("landing"))

    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.view_students"))

    student_name = student.full_name
    hall_ticket = student.hall_ticket

    # Delete related records
    Result.query.filter_by(hall_ticket=hall_ticket).delete()
    Notification.query.filter_by(student_id=student_id).delete()
    AuditLog.query.filter_by(actor_type="student", actor_id=student_id).delete()

    # Delete student
    db.session.delete(student)
    db.session.commit()

    log_audit_event(
        "admin",
        current_user.id,
        "STUDENT_DELETED",
        {"student_name": student_name, "hall_ticket": hall_ticket},
    )

    flash(
        f'Student "{student_name}" ({hall_ticket}) and all their data deleted.',
        "success",
    )
    return redirect(url_for("admin.view_students"))
