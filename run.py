from app import create_app, db
from app.models import Student, Admin, Result, Notification, AuditLog, PDFUpload

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Student': Student,
        'Admin': Admin,
        'Result': Result,
        'Notification': Notification,
        'AuditLog': AuditLog,
        'PDFUpload': PDFUpload
    }

if __name__ == '__main__':
    app.run(debug=True)