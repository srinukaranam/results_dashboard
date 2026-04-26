from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from app.models import Student
import re

BRANCHES = [
    ('CSE', 'Computer Science & Engineering'),
    ('ECE', 'Electronics & Communication'),
    ('EEE', 'Electrical & Electronics'),
    ('MECH', 'Mechanical Engineering'),
    ('CIVIL', 'Civil Engineering'),
    ('IT', 'Information Technology'),
]

YEARS = [(y, str(y)) for y in range(2018, 2027)]

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[
        DataRequired(), Length(min=2, max=50)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(), Length(min=2, max=50)
    ])
    email = StringField('Email', validators=[
        DataRequired(), Email(), Length(max=100)
    ])
    username = StringField('Username', validators=[
        Optional(), Length(min=3, max=50)
    ])
    hall_ticket = StringField('Hall Ticket Number (PIN)', validators=[
        DataRequired(), Length(min=9, max=20)
    ])
    admission_year = SelectField('Admission Year', choices=YEARS, coerce=int, validators=[
        DataRequired()
    ])
    branch = SelectField('Branch', choices=BRANCHES, validators=[
        DataRequired()
    ])
    profile_photo = FileField('Profile Photo (Optional)')
    password = PasswordField('Password', validators=[
        DataRequired(), Length(min=8)
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')
    
    def validate_email(self, field):
        if Student.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')
    
    def validate_username(self, field):
        if field.data and Student.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')
    
    def validate_hall_ticket(self, field):
        if Student.query.filter_by(hall_ticket=field.data).first():
            raise ValidationError('Hall ticket number already registered.')
        
        # Basic JNTUK hall ticket pattern validation
        pattern = r'^[0-9]{2}[A-Z0-9]{1}[0-9A-Z]{1}[A-Z0-9]{1}[0-9]{4}$'
        if not re.match(pattern, field.data.upper()):
            # Don't raise error, just a warning could be shown
            pass


class LoginForm(FlaskForm):
    login_id = StringField('Email or Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class AdminLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Admin Login')