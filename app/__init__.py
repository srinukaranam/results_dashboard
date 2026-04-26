from flask import Flask, render_template
from app.extensions import db, login_manager, migrate, csrf, limiter
from config import config
import os


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    # Initialize mail
    from app.services.email_service import init_mail

    init_mail(app)

    # Login configuration
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Create folders
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)
    os.makedirs(
        os.path.join(app.root_path, "static", "uploads", "profiles"), exist_ok=True
    )

    # Import models AFTER db is initialized
    from app.models import Student, Admin

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith("student_"):
            return db.session.get(Student, int(user_id[8:]))
        elif user_id.startswith("admin_"):
            return db.session.get(Admin, int(user_id[6:]))
        return None

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.student.routes import student_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Landing page
    @app.route("/")
    def landing():
        return render_template("landing.html")

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # CLI command to create admin
    @app.cli.command("create-admin")
    def create_admin():
        """Create an admin user."""
        import getpass
        from app.models import Admin

        with app.app_context():
            db.create_all()

        email = input("Admin email: ")
        full_name = input("Full name: ")
        password = getpass.getpass("Password: ")

        admin = Admin(email=email, full_name=full_name)
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()
        print(f"Admin {email} created successfully.")

    # CLI command to create tables
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        with app.app_context():
            db.create_all()
        print("All database tables created.")

    # Shell context
    @app.shell_context_processor
    def make_shell_context():
        from app.models import Student, Admin, Result, Notification, AuditLog, PDFUpload

        return {
            "db": db,
            "Student": Student,
            "Admin": Admin,
            "Result": Result,
            "Notification": Notification,
            "AuditLog": AuditLog,
            "PDFUpload": PDFUpload,
        }

    return app
