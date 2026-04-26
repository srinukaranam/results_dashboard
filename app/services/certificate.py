"""
Professional Certificate PDF Generator using ReportLab
Features: Photo integration, proper table fitting, watermarks, professional layout
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, grey, white
from reportlab.lib.units import inch, mm, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    Frame,
    PageTemplate,
    BaseDocTemplate,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.platypus.frames import Frame
from reportlab.pdfgen import canvas
from io import BytesIO
import os
from datetime import datetime

from app.extensions import db
from app.models import Result, Student
from app.services.cgpa import (
    calculate_sgpa,
    calculate_cgpa,
    get_semester_results,
    get_year_results,
)

from flask import current_app

# Professional Color Scheme
PRIMARY_DARK = HexColor("#1a2332")  # Dark navy
PRIMARY_BLUE = HexColor("#1e40af")  # Deep blue
ACCENT_GOLD = HexColor("#c9a84c")  # Gold accent
ACCENT_TEAL = HexColor("#0d9488")  # Teal
TEXT_DARK = HexColor("#1e293b")  # Slate 800
TEXT_GRAY = HexColor("#64748b")  # Slate 500
BORDER_LIGHT = HexColor("#e2e8f0")  # Slate 200
BG_LIGHT = HexColor("#f8fafc")  # Slate 50
WHITE_COLOR = white
RED_COLOR = HexColor("#dc2626")
AMBER_COLOR = HexColor("#d97706")
GREEN_COLOR = HexColor("#059669")

GRADE_POINTS = {
    "A+": 10,
    "A": 9,
    "B": 8,
    "C": 7,
    "D": 6,
    "E": 5,
    "F": 0,
    "AB": 0,
    "ABSENT": 0,
    "COMPLE": 0,
}

YEAR_MAP_SEMESTERS = {
    "1": ["1-1", "1-2"],
    "2": ["2-1", "2-2"],
    "3": ["3-1", "3-2"],
    "4": ["4-1", "4-2"],
}

# A4 dimensions
PAGE_W, PAGE_H = A4  # 595.27 x 841.89 points


class ProfessionalCertificate:
    """Base class for professional certificate generation."""

    def __init__(self, buffer, student, include_photo=True):
        self.buffer = buffer
        self.student = student
        self.include_photo = include_photo
        self.width = PAGE_W
        self.height = PAGE_H
        self.margin = 25 * mm

        # Build document with custom page template
        self.doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        # Define frames
        frame = Frame(
            self.margin,
            20 * mm,
            self.width - 2 * self.margin,
            self.height - 40 * mm,
            id="main",
        )
        self.doc.addPageTemplates(
            [PageTemplate(id="main", frames=frame, onPage=self._draw_border)]
        )

        self.elements = []
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Setup custom paragraph styles."""
        self.style_title = ParagraphStyle(
            "CertTitle",
            fontSize=22,
            textColor=PRIMARY_DARK,
            alignment=TA_CENTER,
            spaceAfter=2,
            fontName="Helvetica-Bold",
            leading=28,
        )
        self.style_subtitle = ParagraphStyle(
            "CertSubtitle",
            fontSize=11,
            textColor=TEXT_GRAY,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName="Helvetica",
            leading=15,
        )
        self.style_heading = ParagraphStyle(
            "CertHeading",
            fontSize=14,
            textColor=PRIMARY_DARK,
            alignment=TA_LEFT,
            spaceBefore=12,
            spaceAfter=6,
            fontName="Helvetica-Bold",
            leading=18,
        )
        self.style_normal = ParagraphStyle(
            "CertNormal",
            fontSize=9,
            textColor=TEXT_DARK,
            alignment=TA_LEFT,
            fontName="Helvetica",
            leading=12,
        )
        self.style_watermark = ParagraphStyle(
            "Watermark",
            fontSize=7,
            textColor=HexColor("#94a3b8"),
            alignment=TA_CENTER,
            fontName="Helvetica-Oblique",
        )
        self.style_small = ParagraphStyle(
            "Small",
            fontSize=8,
            textColor=TEXT_GRAY,
            alignment=TA_CENTER,
            fontName="Helvetica",
            leading=10,
        )

    def _draw_border(self, canvas_obj, doc):
        """Draw professional border and header/footer on each page."""
        canvas_obj.saveState()

        # Outer border
        canvas_obj.setStrokeColor(PRIMARY_DARK)
        canvas_obj.setLineWidth(2)
        canvas_obj.rect(15 * mm, 15 * mm, self.width - 30 * mm, self.height - 30 * mm)

        # Inner accent line
        canvas_obj.setStrokeColor(ACCENT_GOLD)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(17 * mm, 17 * mm, self.width - 34 * mm, self.height - 34 * mm)

        # Top decorative bar
        canvas_obj.setFillColor(PRIMARY_DARK)
        canvas_obj.rect(
            15 * mm, self.height - 32 * mm, self.width - 30 * mm, 3 * mm, fill=1
        )

        # Bottom decorative bar
        canvas_obj.rect(15 * mm, 15 * mm, self.width - 30 * mm, 1.5 * mm, fill=1)

        # Gold accent line below top bar
        canvas_obj.setFillColor(ACCENT_GOLD)
        canvas_obj.rect(
            15 * mm, self.height - 33 * mm, self.width - 30 * mm, 0.8 * mm, fill=1
        )

        # Page number
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(TEXT_GRAY)
        canvas_obj.drawCentredString(
            self.width / 2, 18 * mm, f"Page {canvas_obj.getPageNumber()}"
        )

        canvas_obj.restoreState()

    def _add_college_header(self):
        """Add college name and certificate type header."""
        self.elements.append(
            Paragraph("JAWAHARLAL NEHRU TECHNOLOGICAL UNIVERSITY", self.style_title)
        )
        self.elements.append(Paragraph("KAKINADA, ANDHRA PRADESH", self.style_subtitle))
        self.elements.append(Spacer(1, 2 * mm))

        # Gold separator line
        line = Table([[""]], colWidths=[self.width - 2 * self.margin])
        line.setStyle(
            TableStyle(
                [
                    ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT_GOLD),
                ]
            )
        )
        self.elements.append(line)
        self.elements.append(Spacer(1, 4 * mm))

    def _add_student_info_section(self, father_name=None, mother_name=None, dob=None):
        """Add student information with optional photo."""
        info_elements = []

        details = [
            f"<b>Student Name:</b> {self.student.full_name}",
            f"<b>Hall Ticket No:</b> {self.student.hall_ticket}",
            f"<b>Branch:</b> {self.student.branch}",
            f"<b>Admission Year:</b> {self.student.admission_year}",
        ]

        if father_name:
            details.append(f"<b>Father's Name:</b> {father_name}")
        if mother_name:
            details.append(f"<b>Mother's Name:</b> {mother_name}")
        if dob:
            details.append(f"<b>Date of Birth:</b> {dob}")

        # Try to add photo
        photo_added = False
        if self.include_photo and self.student.profile_photo:
            # Search for photo in multiple possible locations
            possible_paths = [
                os.path.join(
                    "app", "static", "uploads", "profiles", self.student.profile_photo
                ),
                os.path.join(
                    current_app.root_path,
                    "static",
                    "uploads",
                    "profiles",
                    self.student.profile_photo,
                ),
            ]

            photo_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    photo_path = path
                    break

            if photo_path:
                try:
                    photo = Image(photo_path, width=28 * mm, height=35 * mm)

                    info_text = "<br/>".join(details)
                    info_para = Paragraph(info_text, self.style_normal)

                    available_width = self.width - 2 * self.margin
                    info_table = Table(
                        [[info_para, photo]],
                        colWidths=[available_width - 32 * mm, 32 * mm],
                    )
                    info_table.setStyle(
                        TableStyle(
                            [
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                                ("LEFTPADDING", (0, 0), (0, 0), 0),
                                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ]
                        )
                    )
                    self.elements.append(info_table)
                    self.elements.append(Spacer(1, 4 * mm))
                    photo_added = True
                except Exception as e:
                    print(f"Photo error: {e}")

        if not photo_added:
            info_text = "<br/>".join(details)
            self.elements.append(Paragraph(info_text, self.style_normal))
            self.elements.append(Spacer(1, 4 * mm))

    def _add_results_table(self, results, title=None, show_sgpa=True, semester=None):
        """Add a professionally formatted results table."""
        if title:
            self.elements.append(Spacer(1, 3 * mm))
            self.elements.append(Paragraph(title, self.style_heading))

        # Calculate column widths based on content
        available_width = self.width - 2 * self.margin

        # Column widths: Code(55) | Subject(remaining) | Credits(45) | Grade(45) | Points(45)
        col_widths = [55, available_width - 235, 45, 45, 45]

        # Header
        header = [
            Paragraph("<b>Code</b>", self.style_small),
            Paragraph("<b>Subject Name</b>", self.style_small),
            Paragraph("<b>Cred</b>", self.style_small),
            Paragraph("<b>Grade</b>", self.style_small),
            Paragraph("<b>Pts</b>", self.style_small),
        ]
        table_data = [header]

        # Data rows
        for r in results:
            grade_color = TEXT_DARK
            if r.grade in ["A+", "A", "B"]:
                grade_color = GREEN_COLOR
            elif r.grade in ["C"]:
                grade_color = AMBER_COLOR
            elif r.grade in ["D", "E"]:
                grade_color = HexColor("#ea580c")
            elif r.grade in ["F", "AB", "ABSENT"]:
                grade_color = RED_COLOR

            subject_name = (
                r.subject_name[:60] + "..."
                if r.subject_name and len(r.subject_name) > 60
                else (r.subject_name or "")
            )

            table_data.append(
                [
                    Paragraph(r.subject_code, self.style_small),
                    Paragraph(subject_name, self.style_small),
                    Paragraph(str(r.credits), self.style_small),
                    Paragraph(
                        f'<font color="{grade_color}"><b>{r.grade}</b></font>',
                        self.style_small,
                    ),
                    Paragraph(str(r.grade_points), self.style_small),
                ]
            )

        # SGPA/CGPA summary row
        if show_sgpa and semester:
            sgpa, sem_credits, _ = calculate_sgpa(self.student.hall_ticket, semester)
            cgpa, cum_credits, _ = calculate_cgpa(self.student.hall_ticket, semester)

            # Add spacer row
            table_data.append([Paragraph("", self.style_small) for _ in range(5)])

            # SGPA row
            table_data.append(
                [
                    Paragraph("", self.style_small),
                    Paragraph("", self.style_small),
                    Paragraph(f"<b>SGPA:</b>", self.style_small),
                    Paragraph(
                        f"<b>{sgpa:.2f}</b>" if sgpa else "N/A", self.style_small
                    ),
                    Paragraph("", self.style_small),
                ]
            )

            # CGPA row
            table_data.append(
                [
                    Paragraph("", self.style_small),
                    Paragraph("", self.style_small),
                    Paragraph(f"<b>CGPA:</b>", self.style_small),
                    Paragraph(
                        f"<b>{cgpa:.2f}</b>" if cgpa else "N/A", self.style_small
                    ),
                    Paragraph("", self.style_small),
                ]
            )

        # Create table
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Style the table
        style_commands = [
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE_COLOR),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            # Data rows
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            # Alignment
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER_LIGHT),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, ACCENT_GOLD),
            # Alternating row colors
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE_COLOR, HexColor("#f1f5f9")]),
        ]

        # Apply styles
        table.setStyle(TableStyle(style_commands))
        self.elements.append(table)

    def _add_footer(self):
        """Add watermark and generation date."""
        self.elements.append(Spacer(1, 8 * mm))

        # Separator
        line = Table([[""]], colWidths=[self.width - 2 * self.margin])
        line.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (0, 0), (-1, 0), 0.5, ACCENT_GOLD),
                ]
            )
        )
        self.elements.append(line)
        self.elements.append(Spacer(1, 4 * mm))

        self.elements.append(
            Paragraph(
                "This is a computer-generated document. UNOFFICIAL - FOR REFERENCE ONLY.",
                self.style_watermark,
            )
        )
        self.elements.append(
            Paragraph(
                f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')} | "
                "JNTUK-Affiliated College, Kakinada",
                self.style_small,
            )
        )

    def build(self):
        """Build the PDF document."""
        self.doc.build(self.elements)
        self.buffer.seek(0)
        return self.buffer


def generate_semester_certificate(
    student, semester, include_photo=True, father_name=None, mother_name=None, dob=None
):
    """Generate professional semester certificate."""
    buffer = BytesIO()

    results = get_semester_results(student.hall_ticket, semester)
    if not results:
        return None

    cert = ProfessionalCertificate(buffer, student, include_photo)

    # Header
    cert._add_college_header()
    cert.elements.append(
        Paragraph(
            f"SEMESTER {semester} - RESULT CERTIFICATE",
            ParagraphStyle(
                "Type",
                fontSize=16,
                textColor=ACCENT_GOLD,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
                leading=20,
            ),
        )
    )
    cert.elements.append(Spacer(1, 5 * mm))

    # Student Info with Photo
    cert._add_student_info_section(father_name, mother_name, dob)

    # Results Table
    cert._add_results_table(results, title="Subject-wise Results", semester=semester)

    # Footer
    cert._add_footer()

    return cert.build()


def generate_year_certificate(
    student, year, include_photo=True, father_name=None, mother_name=None, dob=None
):
    """Generate professional year certificate."""
    buffer = BytesIO()

    results, year_cgpa = get_year_results(student.hall_ticket, year)
    if not results:
        return None

    cert = ProfessionalCertificate(buffer, student, include_photo)

    cert._add_college_header()
    cert.elements.append(
        Paragraph(
            f"YEAR {year} - RESULT CERTIFICATE",
            ParagraphStyle(
                "Type",
                fontSize=16,
                textColor=ACCENT_GOLD,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
                leading=20,
            ),
        )
    )
    cert.elements.append(Spacer(1, 5 * mm))

    cert._add_student_info_section(father_name, mother_name, dob)

    # Year CGPA highlight
    if year_cgpa:
        cert.elements.append(
            Paragraph(
                f"<b>Year {year} CGPA: {year_cgpa:.2f}</b>",
                ParagraphStyle(
                    "YearCGPA",
                    fontSize=12,
                    textColor=ACCENT_TEAL,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                    leading=16,
                ),
            )
        )
        cert.elements.append(Spacer(1, 3 * mm))

    cert._add_results_table(results, title="Subject-wise Results")

    cert._add_footer()

    return cert.build()


def generate_final_certificate(
    student, include_photo=True, father_name=None, mother_name=None, dob=None
):
    """Generate professional final program certificate."""
    buffer = BytesIO()

    results = (
        Result.query.filter_by(hall_ticket=student.hall_ticket, is_supplementary=False)
        .order_by(Result.semester, Result.subject_code)
        .all()
    )

    if not results:
        return None

    cgpa, total_credits, _ = calculate_cgpa(student.hall_ticket)

    cert = ProfessionalCertificate(buffer, student, include_photo)

    cert._add_college_header()
    cert.elements.append(
        Paragraph(
            "FINAL PROGRAM CERTIFICATE",
            ParagraphStyle(
                "Type",
                fontSize=18,
                textColor=ACCENT_GOLD,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
                leading=22,
            ),
        )
    )
    cert.elements.append(Spacer(1, 5 * mm))

    cert._add_student_info_section(father_name, mother_name, dob)

    # Final CGPA highlight box
    cgpa_text = f"FINAL CGPA: {cgpa:.2f}" if cgpa else "FINAL CGPA: N/A"
    credit_text = f"Total Credits Earned: {total_credits}"

    highlight_data = [
        [
            Paragraph(
                cgpa_text,
                ParagraphStyle(
                    "CGPA",
                    fontSize=16,
                    textColor=WHITE_COLOR,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                    leading=20,
                ),
            )
        ],
        [
            Paragraph(
                credit_text,
                ParagraphStyle(
                    "Credits",
                    fontSize=11,
                    textColor=HexColor("#e2e8f0"),
                    alignment=TA_CENTER,
                    fontName="Helvetica",
                    leading=15,
                ),
            )
        ],
    ]

    highlight_table = Table(highlight_data, colWidths=[cert.width - 2 * cert.margin])
    highlight_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_DARK),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ROUNDEDCORNERS", [5, 5, 5, 5]),
            ]
        )
    )
    cert.elements.append(highlight_table)
    cert.elements.append(Spacer(1, 5 * mm))

    # Results by semester
    semesters = sorted(set(r.semester for r in results))

    for sem in semesters:
        sem_results = [r for r in results if r.semester == sem]
        sgpa, _, _ = calculate_sgpa(student.hall_ticket, sem)

        title = f"Semester {sem}"
        if sgpa:
            title += f" — SGPA: {sgpa:.2f}"

        cert._add_results_table(sem_results, title=title)
        cert.elements.append(Spacer(1, 3 * mm))

    cert._add_footer()

    return cert.build()
