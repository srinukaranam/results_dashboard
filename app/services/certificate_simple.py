"""
Professional JNTUK-Style Certificate Generator
Matching JNTUK Provisional Certificate format with photo support
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm, inch
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
from io import BytesIO
import os
from datetime import datetime
from flask import current_app

from app.extensions import db
from app.models import Result
from app.services.cgpa import (
    calculate_sgpa,
    calculate_cgpa,
    get_semester_results,
    get_year_results,
)

PAGE_W, PAGE_H = A4

# JNTUK Official Colors
PRIMARY = HexColor("#0F1923")
GOLD = HexColor("#8B7355")
ACCENT = HexColor("#1a3a5c")
TEXT_DARK = HexColor("#1a1a1a")
TEXT_GRAY = HexColor("#555555")
BORDER_COLOR = HexColor("#c4a97d")
LIGHT_BG = HexColor("#fafaf7")

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


def get_photo_path(student):
    """Find student photo with multiple fallback paths."""
    if not student.profile_photo:
        return None

    possible_paths = [
        os.path.join("app", "static", "uploads", "profiles", student.profile_photo),
        os.path.join(
            current_app.root_path,
            "static",
            "uploads",
            "profiles",
            student.profile_photo,
        ),
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "static",
            "uploads",
            "profiles",
            student.profile_photo,
        ),
    ]

    for p in possible_paths:
        abs_path = os.path.abspath(p)
        if os.path.exists(abs_path):
            return abs_path

    return None


class JNTUKCertificate:
    """Professional JNTUK-style certificate builder."""

    def __init__(self, buffer, student, include_photo=True, college_name=None):
        self.buffer = buffer
        self.student = student
        self.include_photo = include_photo
        self.college_name = college_name
        self.width = PAGE_W
        self.height = PAGE_H
        self.margin = 25 * mm
        self.elements = []
        self._setup_styles()

    def _setup_styles(self):
        """Setup professional paragraph styles."""
        self.style_title = ParagraphStyle(
            "Title",
            fontSize=13,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=1,
            fontName="Times-Bold",
            leading=16,
        )
        self.style_address = ParagraphStyle(
            "Address",
            fontSize=8,
            textColor=TEXT_GRAY,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName="Times-Roman",
            leading=10,
        )
        self.style_cert_type = ParagraphStyle(
            "CertType",
            fontSize=16,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=10,
            fontName="Times-Bold",
            leading=20,
        )
        self.style_body = ParagraphStyle(
            "Body",
            fontSize=10,
            textColor=TEXT_DARK,
            alignment=TA_JUSTIFY,
            fontName="Times-Roman",
            leading=16,
            spaceAfter=6,
        )
        self.style_body_center = ParagraphStyle(
            "BodyCenter",
            fontSize=10,
            textColor=TEXT_DARK,
            alignment=TA_CENTER,
            fontName="Times-Roman",
            leading=16,
            spaceAfter=6,
        )
        self.style_bold = ParagraphStyle(
            "Bold",
            fontSize=10,
            textColor=TEXT_DARK,
            alignment=TA_CENTER,
            fontName="Times-Bold",
            leading=16,
        )
        self.style_small = ParagraphStyle(
            "Small", fontSize=8, textColor=TEXT_DARK, fontName="Times-Roman", leading=11
        )
        self.style_watermark = ParagraphStyle(
            "Watermark",
            fontSize=7,
            textColor=HexColor("#999999"),
            alignment=TA_CENTER,
            fontName="Times-Italic",
        )
        self.style_table_header = ParagraphStyle(
            "TH", fontSize=8, textColor=white, fontName="Times-Bold", leading=10
        )
        self.style_table_cell = ParagraphStyle(
            "TD", fontSize=8, textColor=TEXT_DARK, fontName="Times-Roman", leading=10
        )
        self.style_sem_heading = ParagraphStyle(
            "SemHead",
            fontSize=9,
            textColor=PRIMARY,
            fontName="Times-Bold",
            leading=12,
            spaceBefore=4,
            spaceAfter=2,
        )

    def _draw_border(self, canvas_obj, doc):
        """Draw professional certificate border."""
        canvas_obj.saveState()

        # Outer thin border
        canvas_obj.setStrokeColor(BORDER_COLOR)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.rect(18 * mm, 18 * mm, self.width - 36 * mm, self.height - 36 * mm)

        # Inner border
        canvas_obj.setLineWidth(0.3)
        canvas_obj.rect(20 * mm, 20 * mm, self.width - 40 * mm, self.height - 40 * mm)

        # Top line
        canvas_obj.setStrokeColor(PRIMARY)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(
            20 * mm, self.height - 20 * mm, self.width - 20 * mm, self.height - 20 * mm
        )

        # Bottom line
        canvas_obj.line(20 * mm, 20 * mm, self.width - 20 * mm, 20 * mm)

        canvas_obj.restoreState()

    def add_header(self, cert_title):
        """Add university header."""
        self.elements.append(
            Paragraph(
                "JAWAHARLAL NEHRU TECHNOLOGICAL UNIVERSITY KAKINADA", self.style_title
            )
        )
        self.elements.append(
            Paragraph("KAKINADA - 533 003, ANDHRA PRADESH, INDIA", self.style_address)
        )

        if self.college_name:
            self.elements.append(
                Paragraph(
                    f"<b>College:</b> {self.college_name.upper()}",
                    self.style_body_center,
                )
            )

        self.elements.append(Spacer(1, 3 * mm))
        sep = Table([[""]], colWidths=[self.width - 2 * self.margin])
        sep.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.5, GOLD)]))
        self.elements.append(sep)
        self.elements.append(Spacer(1, 5 * mm))

        self.elements.append(Paragraph(cert_title, self.style_cert_type))
        self.elements.append(Spacer(1, 5 * mm))

    def add_student_info_with_photo(self, info_text):
        """Add student info with optional photo."""
        photo_path = get_photo_path(self.student) if self.include_photo else None

        if photo_path and os.path.exists(photo_path):
            try:
                img = Image(photo_path, width=28 * mm, height=35 * mm)
                available_w = self.width - 2 * self.margin
                info_table = Table(
                    [[Paragraph(info_text, self.style_body), img]],
                    colWidths=[available_w - 32 * mm, 32 * mm],
                )
                info_table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ]
                    )
                )
                self.elements.append(info_table)
            except Exception as e:
                print(f"Photo error: {e}")
                self.elements.append(Paragraph(info_text, self.style_body))
        else:
            self.elements.append(Paragraph(info_text, self.style_body))

        self.elements.append(Spacer(1, 4 * mm))

    def add_results_table(self, results):
        """Add professional results table."""
        available_w = self.width - 2 * self.margin
        col_w = [45, available_w - 190, 45, 50, 50]

        header = [
            Paragraph("<b>Code</b>", self.style_table_header),
            Paragraph("<b>Subject</b>", self.style_table_header),
            Paragraph("<b>Credits</b>", self.style_table_header),
            Paragraph("<b>Grade</b>", self.style_table_header),
            Paragraph("<b>Points</b>", self.style_table_header),
        ]
        table_data = [header]

        for r in results:
            grade_display = r.grade
            if r.is_supple_passed:
                grade_display = f"{r.grade} ★"

            subject_name = r.subject_name if r.subject_name else ""
            if len(subject_name) > 50:
                subject_name = subject_name[:47] + "..."

            table_data.append(
                [
                    Paragraph(r.subject_code, self.style_table_cell),
                    Paragraph(subject_name, self.style_table_cell),
                    Paragraph(str(r.credits), self.style_table_cell),
                    Paragraph(grade_display, self.style_table_cell),
                    Paragraph(str(r.grade_points), self.style_table_cell),
                ]
            )

        t = Table(table_data, colWidths=col_w, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("TOPPADDING", (0, 0), (-1, 0), 6),
                    ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("TOPPADDING", (0, 1), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#c4a97d")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#fdfbf7")]),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, GOLD),
                ]
            )
        )
        self.elements.append(t)

    def add_footer(self):
        """Add footer with date and signatures."""
        self.elements.append(Spacer(1, 10 * mm))

        footer_w = self.width - 2 * self.margin

        footer_data = [
            [
                Paragraph(
                    f"<b>Date:</b> {datetime.now().strftime('%d-%m-%Y')}",
                    self.style_small,
                ),
                Paragraph("", self.style_small),
                Paragraph("", self.style_small),
            ],
            [
                Paragraph("Controller of Examinations", self.style_small),
                Paragraph("Director of Evaluations", self.style_small),
                Paragraph("Registrar", self.style_small),
            ],
        ]

        footer_table = Table(
            footer_data, colWidths=[footer_w / 3, footer_w / 3, footer_w / 3]
        )
        footer_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("TOPPADDING", (0, 0), (-1, -1), 20),
                ]
            )
        )
        self.elements.append(footer_table)

        self.elements.append(Spacer(1, 5 * mm))
        self.elements.append(
            Paragraph(
                "This is a computer-generated document for reference purposes only.",
                self.style_watermark,
            )
        )

    def build(self):
        """Build the PDF."""
        doc = BaseDocTemplate(
            self.buffer,
            pagesize=A4,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=22 * mm,
            bottomMargin=22 * mm,
        )

        frame = Frame(
            self.margin,
            22 * mm,
            self.width - 2 * self.margin,
            self.height - 44 * mm,
            id="main",
        )
        doc.addPageTemplates(
            [PageTemplate(id="main", frames=frame, onPage=self._draw_border)]
        )
        doc.build(self.elements)
        self.buffer.seek(0)
        return self.buffer


def generate_semester_certificate(
    student,
    semester,
    include_photo=True,
    father_name=None,
    mother_name=None,
    dob=None,
    college_name=None,
):
    """Generate semester certificate."""
    buffer = BytesIO()

    results = get_semester_results(student.hall_ticket, semester)
    if not results:
        return None

    sgpa, sem_credits, _ = calculate_sgpa(student.hall_ticket, semester)
    cgpa, cum_credits, _ = calculate_cgpa(student.hall_ticket, semester)

    cert = JNTUKCertificate(buffer, student, include_photo, college_name)
    cert.add_header(f"SEMESTER {semester} - RESULT CERTIFICATE")

    # Student info
    info_text = (
        f"<b>Student Name:</b> {student.full_name}<br/>"
        f"<b>Hall Ticket No:</b> {student.hall_ticket}<br/>"
        f"<b>Branch:</b> {student.branch}<br/>"
        f"<b>Admission Year:</b> {student.admission_year}"
    )
    if father_name:
        info_text += f"<br/><b>Father's Name:</b> {father_name}"
    if mother_name:
        info_text += f"<br/><b>Mother's Name:</b> {mother_name}"
    if dob:
        info_text += f"<br/><b>Date of Birth:</b> {dob}"

    cert.add_student_info_with_photo(info_text)
    cert.add_results_table(results)

    # SGPA/CGPA
    cert.elements.append(Spacer(1, 3 * mm))
    cert.elements.append(
        Paragraph(
            (
                f"<b>SGPA: {sgpa:.2f}</b> &nbsp;&nbsp;|&nbsp;&nbsp; <b>CGPA: {cgpa:.2f}</b>"
                if sgpa and cgpa
                else ""
            ),
            cert.style_bold,
        )
    )

    cert.add_footer()
    return cert.build()


def generate_year_certificate(
    student,
    year,
    include_photo=True,
    father_name=None,
    mother_name=None,
    dob=None,
    college_name=None,
):
    """Generate year certificate."""
    buffer = BytesIO()

    results, year_cgpa = get_year_results(student.hall_ticket, year)
    if not results:
        return None

    cert = JNTUKCertificate(buffer, student, include_photo, college_name)
    cert.add_header(f"YEAR {year} - RESULT CERTIFICATE")

    info_text = (
        f"<b>Student Name:</b> {student.full_name}<br/>"
        f"<b>Hall Ticket No:</b> {student.hall_ticket}<br/>"
        f"<b>Branch:</b> {student.branch}"
    )
    cert.add_student_info_with_photo(info_text)

    if year_cgpa:
        cert.elements.append(
            Paragraph(f"<b>Year {year} CGPA: {year_cgpa:.2f}</b>", cert.style_bold)
        )
        cert.elements.append(Spacer(1, 3 * mm))

    cert.add_results_table(results)
    cert.add_footer()
    return cert.build()


def generate_final_certificate(
    student,
    include_photo=True,
    father_name=None,
    mother_name=None,
    dob=None,
    college_name=None,
):
    """Generate final provisional certificate matching JNTUK format exactly."""
    buffer = BytesIO()

    cgpa, total_credits, _ = calculate_cgpa(student.hall_ticket)

    # Determine class/division
    if cgpa and cgpa >= 7.0:
        division = "FIRST CLASS WITH DISTINCTION"
    elif cgpa and cgpa >= 6.0:
        division = "FIRST CLASS"
    elif cgpa and cgpa >= 5.0:
        division = "SECOND CLASS"
    else:
        division = "PASS CLASS"

    cert = JNTUKCertificate(buffer, student, include_photo, college_name)

    # ===== UNIVERSITY HEADER =====
    cert.elements.append(
        Paragraph(
            "JAWAHARLAL NEHRU TECHNOLOGICAL UNIVERSITY KAKINADA", cert.style_title
        )
    )
    cert.elements.append(
        Paragraph("KAKINADA - 533 003, ANDHRA PRADESH, INDIA", cert.style_address)
    )

    # College name
    if college_name:
        cert.elements.append(
            Paragraph(f"<b>College:</b> {college_name.upper()}", cert.style_body_center)
        )

    cert.elements.append(Spacer(1, 5 * mm))

    # ===== CERTIFICATE TITLE =====
    cert.elements.append(
        Paragraph(
            "PROVISIONAL CERTIFICATE",
            ParagraphStyle(
                "CertTitle",
                fontSize=18,
                textColor=PRIMARY,
                alignment=TA_CENTER,
                fontName="Times-Bold",
                spaceAfter=8,
                leading=22,
            ),
        )
    )

    cert.elements.append(Spacer(1, 5 * mm))

    # ===== CERTIFICATE BODY TEXT =====
    # Build the certificate text exactly like JNTUK format
    body_lines = []

    # Line 1: This is to certify that STUDENT NAME
    body_lines.append(f"This is to certify that <b>{student.full_name.upper()}</b>")

    # Line 2: Son/Daughter of
    if father_name:
        body_lines.append(f"Son/Daughter of <b>SHRI {father_name.upper()}</b>")
    elif mother_name:
        body_lines.append(f"Son/Daughter of <b>SMT. {mother_name.upper()}</b>")

    if father_name and mother_name:
        body_lines[-1] = (
            f"Son/Daughter of <b>SHRI {father_name.upper()}</b> and <b>SMT. {mother_name.upper()}</b>"
        )

    # Line 3: Hall Ticket and Degree info
    body_lines.append(
        f"bearing Hall Ticket No. <b>{student.hall_ticket}</b> "
        f"passed <b>B.TECH ({student.branch})</b> degree "
        f"examination of this university "
        f"and that he/she was placed in <b>{division}</b>"
    )

    # Line 4: CGPA
    if cgpa:
        body_lines.append(
            f"with a Cumulative Grade Point Average (CGPA) of <b>{cgpa:.2f}</b> "
            f"and Total Credits Earned: <b>{total_credits}</b>"
        )

    # Join all lines
    body_text = "<br/>".join(body_lines)

    # Add photo if available
    photo_path = get_photo_path(student) if include_photo else None

    if photo_path and os.path.exists(photo_path):
        try:
            img = Image(photo_path, width=28 * mm, height=35 * mm)
            available_w = PAGE_W - 2 * cert.margin

            # Body text on left, photo on right
            info_table = Table(
                [[Paragraph(body_text, cert.style_body), img]],
                colWidths=[available_w - 32 * mm, 32 * mm],
            )
            info_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            cert.elements.append(info_table)
        except Exception as e:
            print(f"Photo error: {e}")
            cert.elements.append(Paragraph(body_text, cert.style_body))
    else:
        cert.elements.append(Paragraph(body_text, cert.style_body))

    cert.elements.append(Spacer(1, 8 * mm))

    # ===== SATISFACTION STATEMENT =====
    cert.elements.append(
        Paragraph(
            "He/She has satisfied all the requirements for the award of the B.Tech degree "
            "of the Jawaharlal Nehru Technological University Kakinada.",
            cert.style_body,
        )
    )

    cert.elements.append(Spacer(1, 15 * mm))

    # ===== FOOTER WITH SIGNATURES =====
    footer_w = PAGE_W - 2 * cert.margin

    # Date
    cert.elements.append(
        Paragraph(
            f"<b>Date:</b> {datetime.now().strftime('%d-%m-%Y')}",
            ParagraphStyle(
                "Date",
                fontSize=9,
                textColor=TEXT_DARK,
                alignment=TA_LEFT,
                fontName="Times-Roman",
                leading=12,
            ),
        )
    )
    cert.elements.append(Spacer(1, 10 * mm))

    # Signature lines
    footer_data = [
        [
            Paragraph("Controller of Examinations", cert.style_small),
            Paragraph("Director of Evaluations", cert.style_small),
            Paragraph("Registrar", cert.style_small),
        ]
    ]

    footer_table = Table(
        footer_data, colWidths=[footer_w / 3, footer_w / 3, footer_w / 3]
    )
    footer_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("TOPPADDING", (0, 0), (-1, -1), 15),
            ]
        )
    )
    cert.elements.append(footer_table)

    # ===== WATERMARK =====
    cert.elements.append(Spacer(1, 10 * mm))
    cert.elements.append(
        Paragraph(
            "This is a computer-generated document for reference purposes only.",
            cert.style_watermark,
        )
    )

    # ===== BUILD =====
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=30 * mm,
        rightMargin=30 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    frame = Frame(
        30 * mm,
        25 * mm,
        PAGE_W - 60 * mm,
        PAGE_H - 50 * mm,
        id="main",
    )
    doc.addPageTemplates(
        [PageTemplate(id="main", frames=frame, onPage=cert._draw_border)]
    )
    doc.build(cert.elements)
    buffer.seek(0)
    return buffer
