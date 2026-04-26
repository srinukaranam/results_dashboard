from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, SelectField
from wtforms.validators import DataRequired

SEMESTERS = [
    ('1-1', '1-1 (First Year - Sem 1)'),
    ('1-2', '1-2 (First Year - Sem 2)'),
    ('2-1', '2-1 (Second Year - Sem 1)'),
    ('2-2', '2-2 (Second Year - Sem 2)'),
    ('3-1', '3-1 (Third Year - Sem 1)'),
    ('3-2', '3-2 (Third Year - Sem 2)'),
    ('4-1', '4-1 (Fourth Year - Sem 1)'),
    ('4-2', '4-2 (Fourth Year - Sem 2)'),
]

class PDFUploadForm(FlaskForm):
    pdf_file = FileField('JNTUK Result PDF', validators=[
        FileRequired(),
        FileAllowed(['pdf'], 'PDF files only!')
    ])
    semester = SelectField('Semester', choices=SEMESTERS, validators=[DataRequired()])
    submit = SubmitField('Upload & Parse')