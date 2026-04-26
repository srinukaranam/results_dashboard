from datetime import datetime, timedelta
from flask_login import UserMixin
from app.extensions import db  # Changed from: from app import db
import bcrypt


class Student(UserMixin, db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    hall_ticket = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    branch = db.Column(db.String(10))
    admission_year = db.Column(db.Integer, nullable=False)
    profile_photo = db.Column(db.Text)

    # Email Verification
    is_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, default=0)

    # Login tracking
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    results = db.relationship("Result", backref="student", lazy=True)
    notifications = db.relationship("Notification", backref="student", lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(12)
        ).decode("utf-8")

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def increment_failed_attempts(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)

    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None

    def get_id(self):
        return f"student_{self.id}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Admin(UserMixin, db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))

    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(12)
        ).decode("utf-8")

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def increment_failed_attempts(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)

    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None

    def get_id(self):
        return f"admin_{self.id}"


class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    hall_ticket = db.Column(
        db.String(20), db.ForeignKey("students.hall_ticket"), nullable=False
    )
    semester = db.Column(db.String(5), nullable=False)
    subject_code = db.Column(db.String(10), nullable=False)
    subject_name = db.Column(db.String(100))
    credits = db.Column(db.Float)
    grade = db.Column(db.String(5))
    grade_points = db.Column(db.Float)
    is_supplementary = db.Column(db.Boolean, default=False)
    is_supple_passed = db.Column(db.Boolean, default=False)  # ADD THIS: Star indicator
    pdf_source = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "hall_ticket", "semester", "subject_code", name="unique_result"
        ),
    )


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    semester = db.Column(db.String(5))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_type = db.Column(db.String(10))
    actor_id = db.Column(db.Integer)
    event_type = db.Column(db.String(50))
    ip_address = db.Column(db.String(45))
    extra_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PDFUpload(db.Model):
    __tablename__ = "pdf_uploads"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"))
    filename = db.Column(db.String(255))
    file_hash = db.Column(db.String(64))
    total_rows = db.Column(db.Integer)
    success_count = db.Column(db.Integer)
    error_count = db.Column(db.Integer)
    status = db.Column(db.String(20), default="pending")
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("Admin", backref="uploads")
