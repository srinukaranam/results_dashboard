# 🎓 Result Dashboard System

A secure, full-stack web application for JNTUK-affiliated colleges to manage student results, calculate CGPA, and generate professional certificates.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![Tailwind](https://img.shields.io/badge/Tailwind-CSS-06B6D4.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📸 Screenshots

| Landing Page | Student Dashboard |
|:------------:|:-----------------:|
| Cyber-themed landing with matrix rain effect | Dark theme dashboard with CGPA charts |

| Admin Panel | Certificate |
|:-----------:|:-----------:|
| PDF upload & student management | Professional JNTUK-style certificates |

---

## 🚀 Features

### 🔐 Authentication & Security
- **Student Registration** with email OTP verification
- **Admin Login** with pre-seeded credentials (no public registration)
- **bcrypt** password hashing
- **CSRF Protection** on all forms
- **Rate Limiting** on login/register endpoints
- **Session Management** with auto-expiry
- **Brute Force Protection** (account lockout after 5 failed attempts)
- **Audit Logging** for all authentication events

### 📄 PDF Parsing Engine
- **Multi-branch PDF Support** - Parses all branches from JNTUK result PDFs
- **Intelligent Extraction** - Hall ticket detection, subject code matching
- **Branch Detection** - Auto-identifies branch from hall ticket prefix
- **Supplementary Results** - Detects and flags supplementary exam results
- **Duplicate Prevention** - Upserts results to avoid data corruption
- **Progress Tracking** - Admin can view parse logs and errors

### 📊 Student Dashboard
- **Semester-wise Results** - View results for any semester (1-1 to 4-2)
- **Year-wise Results** - Combined view with cumulative CGPA
- **Real-time CGPA/SGPA** - Auto-calculated using JNTUK R20 formula
- **Performance Charts** - SGPA trend line chart, grade distribution bar chart
- **Credit Progress Tracker** - Visual progress bar towards graduation
- **Weak Subject Detection** - Highlights subjects needing improvement
- **Supplementary Results** - Separate section with ⭐ indicator for passed subjects
- **Notification System** - Bell icon alerts when new results uploaded

### 📜 Certificate Generator
- **Semester Certificate** - Single semester with photo and SGPA
- **Year Certificate** - Combined academic year with CGPA
- **Final Certificate** - Complete program summary matching JNTUK format
- **Photo Integration** - Student profile photo on all certificates
- **Optional Fields** - Father's name, Mother's name, Date of Birth
- **College Name** - Customizable college name field
- **Professional Layout** - JNTUK border style, gold accents, Times font
- **Class/Division** - Auto-calculated: Distinction, First, Second, Pass

### 📈 Analytics
- **SGPA/CGPA Trend Chart** - Line chart across all semesters
- **Grade Distribution** - Bar chart showing grade frequency
- **Credit Progress** - Visual progress with percentage
- **Focus Areas** - Weak subjects highlighted with grade badges
- **Overview Stats** - CGPA, Credits, Backlogs, Completed Semesters

### 🛡️ Admin Panel
- **PDF Upload** - Drag-and-drop with semester selection
- **Parse Logs** - Real-time parse status with success/error counts
- **Student Management** - Search, view, and delete students
- **Audit Logs** - Chronological event tracking with IP addresses
- **System Status** - Database health, storage usage, failed login monitoring
- **Upload History** - View all PDF uploads with detailed results

### 🌐 Landing Page
- **Cyber/Ethical Hacker Theme** - Dark navy with cyan neon accents
- **Matrix Rain Effect** - Animated falling characters
- **Grid Background** - Moving grid lines
- **Typewriter Effect** - Rotating tagline phrases
- **Scroll Animations** - Fade-in reveals on scroll
- **Mobile Responsive** - Hamburger menu for mobile

---

## 🎯 JNTUK Grading System (R20)

| Grade | Points | Description |
|:-----:|:------:|:------------|
| A+ | 10 | Outstanding |
| A | 9 | Excellent |
| B | 8 | Very Good |
| C | 7 | Good |
| D | 6 | Average |
| E | 5 | Below Average |
| F | 0 | Fail |
| AB | 0 | Absent |
| COMPLE | 0 | Completed (0 credits) |

### CGPA Formula
SGPA = Σ(Credit × Grade Points) / Σ Credits [per semester]
CGPA = Σ(Credit × Grade Points) / Σ Credits [all semesters]


---

## 🏗️ Architecture
┌─────────────────────────────────────────────────────────┐
│ FRONTEND (HTML5 + Tailwind CSS + JS) │
├─────────────────────────────────────────────────────────┤
│ BACKEND (Python Flask) │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │ Auth │ │ Parser │ │ CGPA │ │ Cert │ │
│ │ Module │ │ Engine │ │ Engine │ │ Engine │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────┤
│ DATABASE (SQLite/PostgreSQL) │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │ Students │ │ Results │ │ Admins │ │ Audit │ │
│ │ │ │ │ │ │ │ Logs │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────┘


---

## 📁 Project Structure
result-dashboard/
├── app/
│ ├── init.py # Flask app factory
│ ├── extensions.py # Flask extensions
│ ├── models.py # Database models
│ ├── auth/
│ │ ├── init.py
│ │ ├── routes.py # Auth routes (login/register/OTP)
│ │ └── forms.py # Registration & login forms
│ ├── student/
│ │ ├── init.py
│ │ └── routes.py # Student dashboard & certificate routes
│ ├── admin/
│ │ ├── init.py
│ │ ├── routes.py # Admin routes (upload/manage)
│ │ └── forms.py # PDF upload form
│ ├── services/
│ │ ├── init.py
│ │ ├── pdf_parser.py # JNTUK PDF parsing engine
│ │ ├── cgpa.py # CGPA/SGPA calculator
│ │ ├── certificate_simple.py # Professional certificate generator
│ │ └── email_service.py # OTP email service
│ ├── templates/
│ │ ├── landing.html # Cyber-themed landing page
│ │ ├── base.html # Base template
│ │ ├── auth/
│ │ │ ├── login.html # Student login
│ │ │ ├── register.html # Student registration
│ │ │ └── verify_email.html # OTP verification
│ │ ├── student/
│ │ │ ├── dashboard.html # Main student dashboard
│ │ │ ├── analytics.html # Performance analytics
│ │ │ ├── semester.html # Semester results
│ │ │ ├── year.html # Year results
│ │ │ ├── certificates.html # Certificate generator
│ │ │ ├── profile.html # Profile editor
│ │ │ └── notifications.html # Notifications
│ │ ├── admin/
│ │ │ ├── login.html # Admin login
│ │ │ ├── dashboard.html # Admin dashboard
│ │ │ ├── students.html # Student management
│ │ │ ├── uploads.html # Upload history
│ │ │ ├── upload_results.html # Upload result details
│ │ │ ├── audit_logs.html # Audit log viewer
│ │ │ └── system_status.html # System health
│ │ └── errors/
│ │ ├── 404.html # 404 error page
│ │ └── 500.html # 500 error page
│ └── static/
│ ├── css/
│ │ └── landing.css # Landing page animations
│ ├── js/
│ └── uploads/
│ └── profiles/ # Student profile photos
├── migrations/ # Database migrations
├── uploads/ # Uploaded PDFs
├── .env.example # Environment variables template
├── .gitignore
├── config.py # App configuration
├── requirements.txt # Python dependencies
├── run.py # Application entry point
└── README.md

## 🗄️ Database Schema

### students
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| hall_ticket | VARCHAR(20) | Unique JNTUK hall ticket number |
| first_name | VARCHAR(50) | First name |
| last_name | VARCHAR(50) | Last name |
| email | VARCHAR(100) | Unique email address |
| username | VARCHAR(50) | Optional username |
| password_hash | VARCHAR(255) | bcrypt hashed password |
| branch | VARCHAR(10) | CSE, ECE, EEE, MECH, CIVIL, IT |
| admission_year | INTEGER | Year of admission |
| profile_photo | TEXT | Profile photo file path |
| is_verified | BOOLEAN | Email verification status |
| otp_code | VARCHAR(6) | OTP for email verification |
| otp_expiry | DATETIME | OTP expiration time |
| otp_attempts | INTEGER | Failed OTP attempts |
| failed_login_attempts | INTEGER | Failed login attempts |
| locked_until | DATETIME | Account lockout time |

### results
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| hall_ticket | VARCHAR(20) | Foreign key to students |
| semester | VARCHAR(5) | Semester (1-1, 1-2, ..., 4-2) |
| subject_code | VARCHAR(10) | JNTUK subject code |
| subject_name | VARCHAR(100) | Subject name |
| credits | FLOAT | Credit hours |
| grade | VARCHAR(5) | Grade (A+, A, B, C, D, E, F) |
| grade_points | FLOAT | Grade points |
| is_supplementary | BOOLEAN | Supplementary exam flag |
| is_supple_passed | BOOLEAN | Passed in supplementary ⭐ |
| pdf_source | VARCHAR(255) | Source PDF filename |

### admins
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| email | VARCHAR(100) | Unique admin email |
| password_hash | VARCHAR(255) | bcrypt hashed password |
| full_name | VARCHAR(100) | Admin name |

### notifications
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| student_id | INTEGER | Foreign key to students |
| message | TEXT | Notification message |
| semester | VARCHAR(5) | Related semester |
| is_read | BOOLEAN | Read status |

### audit_logs
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| actor_type | VARCHAR(10) | "student" or "admin" |
| actor_id | INTEGER | Actor's ID |
| event_type | VARCHAR(50) | Event type |
| ip_address | VARCHAR(45) | IP address |
| extra_data | TEXT | Additional JSON data |

### pdf_uploads
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| admin_id | INTEGER | Uploading admin |
| filename | VARCHAR(255) | Original filename |
| file_hash | VARCHAR(64) | SHA-256 hash |
| total_rows | INTEGER | Total parsed rows |
| success_count | INTEGER | Successful inserts |
| error_count | INTEGER | Failed inserts |
| status | VARCHAR(20) | pending/processing/done/failed |

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend** | Python 3.11+, Flask 3.x |
| **Frontend** | HTML5, Tailwind CSS, Vanilla JavaScript |
| **Charts** | Chart.js 4.x |
| **Database** | SQLite (Dev) / PostgreSQL (Prod) |
| **ORM** | SQLAlchemy + Flask-SQLAlchemy |
| **Auth** | Flask-Login + bcrypt |
| **Forms** | Flask-WTF (CSRF Protection) |
| **Rate Limiting** | Flask-Limiter |
| **PDF Parsing** | pdfplumber + PyMuPDF |
| **PDF Generation** | ReportLab |
| **Email** | Flask-Mail (Gmail SMTP) |
| **Migrations** | Flask-Migrate (Alembic) |
| **Fonts** | JetBrains Mono, Inter, Times New Roman |

---

## 📦 Installation

### Prerequisites
- Python 3.11 or higher
- Git
- PostgreSQL (optional, SQLite used by default)

### Step 1: Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/result-dashboard.git
cd result-dashboard
Step 2: Create Virtual Environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

Step 3: Install Dependencies
pip install -r requirements.txt

Step 4: Configure Environment
# Copy the example env file
cp .env.example .env

# Edit .env with your settings
# Required: SECRET_KEY, MAIL_USERNAME, MAIL_PASSWORD

Step 5: Initialize Database
flask init-db

Step 6: Create Admin User
flask create-admin
# Enter admin email, name, and password when prompted

Step 7: Run the Application
python run.py

Step 8: Access the Application
Landing Page: http://127.0.0.1:5000

Student Registration: http://127.0.0.1:5000/auth/register

Student Login: http://127.0.0.1:5000/auth/login

Admin Login: http://127.0.0.1:5000/admin/login
