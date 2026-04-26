from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    send_file,
    current_app,
)
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Student, Result, Notification
from app.services.cgpa import (
    calculate_sgpa,
    calculate_cgpa,
    get_semester_results,
    get_year_results,
    get_supplementary_results,
    get_weak_subjects,
    get_backlog_count,
    get_completed_semesters,
    ALL_SEMESTERS,
    YEAR_MAP,
)
from app.services.certificate_simple import (
    generate_semester_certificate,
    generate_year_certificate,
    generate_final_certificate,
)
from datetime import datetime
import os
from werkzeug.utils import secure_filename

student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard")
@login_required
def dashboard():
    if not isinstance(current_user, Student):
        flash("Access denied.", "danger")
        return redirect(url_for("landing"))

    unread_count = Notification.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    completed_semesters = get_completed_semesters(current_user.hall_ticket)
    cgpa, total_credits, _ = calculate_cgpa(current_user.hall_ticket)
    latest_semester = completed_semesters[-1] if completed_semesters else None
    backlogs = get_backlog_count(current_user.hall_ticket)

    latest_results = None
    if latest_semester:
        latest_results = get_semester_results(current_user.hall_ticket, latest_semester)

    weak_subjects = get_weak_subjects(current_user.hall_ticket)
    supple_results = get_supplementary_results(current_user.hall_ticket)

    # Prepare chart data
    semester_labels = []
    sgpa_values = []
    cgpa_values = []

    for sem in completed_semesters:
        semester_labels.append(f"Sem {sem}")
        sgpa, _, _ = calculate_sgpa(current_user.hall_ticket, sem)
        cgpa_val, _, _ = calculate_cgpa(current_user.hall_ticket, sem)
        sgpa_values.append(float(sgpa) if sgpa else 0)
        cgpa_values.append(float(cgpa_val) if cgpa_val else 0)

    return render_template(
        "student/dashboard.html",
        student=current_user,
        unread_count=unread_count,
        cgpa=cgpa,
        total_credits=total_credits,
        backlogs=backlogs,
        latest_semester=latest_semester,
        latest_results=latest_results,
        weak_subjects=weak_subjects,
        supple_results=supple_results,
        completed_semesters=completed_semesters,
        all_semesters=ALL_SEMESTERS,
        semester_labels=semester_labels,
        sgpa_values=sgpa_values,
        cgpa_values=cgpa_values,
    )


@student_bp.route("/results/<semester>")
@login_required
def view_semester(semester):
    if not isinstance(current_user, Student):
        flash("Access denied.", "danger")
        return redirect(url_for("landing"))

    results = get_semester_results(current_user.hall_ticket, semester)
    sgpa, total_credits, _ = calculate_sgpa(current_user.hall_ticket, semester)
    cgpa, cum_credits, _ = calculate_cgpa(current_user.hall_ticket, semester)

    return render_template(
        "student/semester.html",
        student=current_user,
        semester=semester,
        results=results,
        sgpa=sgpa,
        cgpa=cgpa,
        total_credits=total_credits,
    )


@student_bp.route("/results/year/<year>")
@login_required
def view_year(year):
    if not isinstance(current_user, Student):
        flash("Access denied.", "danger")
        return redirect(url_for("landing"))

    results, year_cgpa = get_year_results(current_user.hall_ticket, year)

    return render_template(
        "student/year.html",
        student=current_user,
        year=year,
        results=results,
        year_cgpa=year_cgpa,
    )


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if not isinstance(current_user, Student):
        return redirect(url_for("landing"))

    if request.method == "POST":
        # Update text fields
        current_user.first_name = request.form.get(
            "first_name", current_user.first_name
        )
        current_user.last_name = request.form.get("last_name", current_user.last_name)
        current_user.email = request.form.get("email", current_user.email)
        current_user.username = request.form.get("username", current_user.username)

        # Handle profile photo upload
        if "profile_photo" in request.files:
            file = request.files["profile_photo"]
            if file and file.filename and file.filename != "":
                filename = secure_filename(
                    f"{current_user.hall_ticket}_{file.filename}"
                )

                # Save to static folder so it's accessible
                upload_dir = os.path.join(
                    current_app.root_path, "static", "uploads", "profiles"
                )
                os.makedirs(upload_dir, exist_ok=True)

                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)

                # Store relative path
                current_user.profile_photo = filename
                print(f"Photo saved: {filepath}")

        # Handle password change
        if request.form.get("password"):
            current_user.set_password(request.form.get("password"))

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("student.profile"))

    return render_template("student/profile.html", student=current_user)


@student_bp.route("/notifications")
@login_required
def notifications():
    if not isinstance(current_user, Student):
        return jsonify({"error": "Unauthorized"}), 403

    notifications = (
        Notification.query.filter_by(student_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    return render_template(
        "student/notifications.html",
        student=current_user,  # ADD THIS
        notifications=notifications,
    )


@student_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    if not isinstance(current_user, Student):
        return jsonify({"error": "Unauthorized"}), 403

    notification = db.session.get(Notification, notification_id)
    if not notification or notification.student_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    notification.is_read = True
    db.session.commit()

    return jsonify({"success": True})


@student_bp.route("/certificates")
@login_required
def certificates():
    if not isinstance(current_user, Student):
        return redirect(url_for("landing"))

    completed_semesters = get_completed_semesters(current_user.hall_ticket)
    years = []
    for year_num in ["1", "2", "3", "4"]:
        semesters = YEAR_MAP.get(year_num, [])
        if any(s in completed_semesters for s in semesters):
            years.append(year_num)

    return render_template(
        "student/certificates.html",
        student=current_user,  # ADD THIS
        completed_semesters=completed_semesters,
        years=years,
    )


@student_bp.route("/certificates/generate/<cert_type>/<value>")
@login_required
def generate_certificate(cert_type, value):
    """Generate and download certificate PDF."""
    if not isinstance(current_user, Student):
        return redirect(url_for("landing"))

    # Get optional fields
    college_name = request.args.get("college_name", "")
    father_name = request.args.get("father_name", "")
    mother_name = request.args.get("mother_name", "")
    dob = request.args.get("dob", "")

    try:
        buffer = None
        filename = ""

        if cert_type == "semester":
            buffer = generate_semester_certificate(
                current_user,
                value,
                include_photo=True,
                college_name=college_name if college_name else None,
                father_name=father_name if father_name else None,
                mother_name=mother_name if mother_name else None,
                dob=dob if dob else None,
            )
            filename = f"Semester_{value}_Certificate_{current_user.hall_ticket}.pdf"

        elif cert_type == "year":
            buffer = generate_year_certificate(
                current_user,
                value,
                include_photo=True,
                college_name=college_name if college_name else None,
                father_name=father_name if father_name else None,
                mother_name=mother_name if mother_name else None,
                dob=dob if dob else None,
            )
            filename = f"Year_{value}_Certificate_{current_user.hall_ticket}.pdf"

        elif cert_type == "final":
            buffer = generate_final_certificate(
                current_user,
                include_photo=True,
                college_name=college_name if college_name else None,
                father_name=father_name if father_name else None,
                mother_name=mother_name if mother_name else None,
                dob=dob if dob else None,
            )
            filename = f"Final_Certificate_{current_user.hall_ticket}.pdf"

        if buffer is None:
            flash("No results available for this selection.", "warning")
            return redirect(url_for("student.certificates"))

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        flash(f"Error generating certificate: {str(e)}", "danger")
        return redirect(url_for("student.certificates"))


@student_bp.route("/analytics")
@login_required
def analytics():
    if not isinstance(current_user, Student):
        return redirect(url_for("landing"))

    # Get all results
    results = (
        Result.query.filter_by(
            hall_ticket=current_user.hall_ticket, is_supplementary=False
        )
        .order_by(Result.semester)
        .all()
    )

    # Get completed semesters with SGPA
    completed_semesters = get_completed_semesters(current_user.hall_ticket)

    semester_labels = []
    sgpa_values = []
    cgpa_values = []

    for sem in completed_semesters:
        semester_labels.append(f"Sem {sem}")
        sgpa, _, _ = calculate_sgpa(current_user.hall_ticket, sem)
        cgpa, _, _ = calculate_cgpa(current_user.hall_ticket, sem)
        sgpa_values.append(float(sgpa) if sgpa else 0)
        cgpa_values.append(float(cgpa) if cgpa else 0)

    # Grade distribution
    grade_counts = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0, "AB": 0}
    for r in results:
        grade = r.grade if r.grade in grade_counts else "F"
        if grade in grade_counts:
            grade_counts[grade] += 1

    # Credit progress
    total_credits_earned = sum(
        float(r.credits)
        for r in results
        if r.grade not in ["F", "AB", "ABSENT", "COMPLE"] and r.credits
    )
    total_credits_attempted = sum(
        float(r.credits) for r in results if r.grade != "COMPLE" and r.credits
    )
    total_program_credits = 180  # Typical 4-year program

    # Weak subjects for focused improvement
    weak_subjects = get_weak_subjects(current_user.hall_ticket)

    # Backlog count
    backlogs = get_backlog_count(current_user.hall_ticket)

    # Current CGPA
    cgpa, cum_credits, _ = calculate_cgpa(current_user.hall_ticket)

    return render_template(
        "student/analytics.html",
        student=current_user,
        semester_labels=semester_labels,
        sgpa_values=sgpa_values,
        cgpa_values=cgpa_values,
        grade_counts=grade_counts,
        total_credits_earned=total_credits_earned,
        total_credits_attempted=total_credits_attempted,
        total_program_credits=total_program_credits,
        weak_subjects=weak_subjects,
        backlogs=backlogs,
        cgpa=cgpa,
        cum_credits=cum_credits,
        completed_semesters=completed_semesters,
    )
