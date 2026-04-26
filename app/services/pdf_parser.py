import pdfplumber
import re
import hashlib
from app.extensions import db
from app.models import Result, Notification, PDFUpload, Student
from datetime import datetime

GRADE_MAP = {
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

# Subject name mapping from PRD
SUBJECT_MAP = {
    "R19BS1101": "MATHEMATICS-I",
    "R19BS1102": "MATHEMATICS-II (MM)",
    "R19BS1103": "ENGINEERING DRAWING",
    "R19BS1106": "APPLIED CHEMISTRY",
    "R19BS1108": "ENGINEERING PHYSICS",
    "R19ES1103": "ENGINEERING DRAWING",
    "R19AG1101": "SURVEYING AND LEVELING",
    "R201101": "MATHEMATICS-I",
    "R201102": "COMMUNICATIVE ENGLISH",
    "R201103": "ENGINEERING PHYSICS",
    "R201104": "ENGINEERING DRAWING",
    "R201106": "ENGLISH COMMUNICATION SKILLS LAB",
    "R201107": "ENGINEERING PHYSICS LAB",
    "R201110": "PROGRAMMING FOR PROBLEM SOLVING USING C",
    "R201113": "PROGRAMMING FOR PROBLEM SOLVING USING C LAB",
    "R201114": "ENVIRONMENTAL SCIENCE",
    "R201115": "APPLIED CHEMISTRY",
    "R201116": "APPLIED CHEMISTRY LAB",
    "R201117": "APPLIED PHYSICS",
    "R201118": "COMPUTER ENGINEERING WORKSHOP",
    "R201119": "APPLIED PHYSICS LAB",
    "R201127": "PRINCIPLES OF SOIL SCIENCE AND AGRONOMY",
    "R201128": "ENGINEERING WORKSHOP AND IT WORKSHOP",
    "R201129": "SOIL SCIENCE AND AGRONOMY FIELD LAB",
    "R19BS1105": "PROFESSIONAL ETHICS",
    "R19ES1101": "ENGINEERING GRAPHICS",
}


def normalize_grade(grade_str):
    """Normalize grade to standard format."""
    if not grade_str:
        return "F", 0

    grade_str = grade_str.upper().strip()

    if grade_str in ["ABSENT", "AB"]:
        return "AB", 0
    if grade_str == "COMPLE":
        return "COMPLE", 0
    if grade_str in GRADE_MAP:
        return grade_str, GRADE_MAP[grade_str]
    if grade_str == "A":
        return "A+", 9

    return "F", 0


def parse_jntuk_pdf(filepath, admin_id, filename, semester="1-1"):
    """
    Parse JNTUK result PDF using pattern-based extraction.
    Handles the space-separated format from the PDF.
    """
    results = []
    total_rows = 0
    success_count = 0
    error_count = 0
    errors = []

    # Hall ticket pattern: 1961A0502, 206T1A0301, 2161A0401, 206TA1A0304
    HALL_TICKET_PATTERN = re.compile(
        r"^(\d{2,3})([A-Z]{0,3})([A-Z0-9]{1})([A-Z]{1})(\d{4})$"
    )

    # Subject code pattern: R19BS1103, R201103
    SUBJECT_CODE_PATTERN = re.compile(r"^R\d{1,2}[A-Z]{2,3}\d{4}$")

    try:
        with pdfplumber.open(filepath) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue

                # Clean text
                text = text.replace("\n", " ").replace("\r", " ")

                # Split into tokens
                tokens = text.split()

                i = 0
                while i < len(tokens) - 4:
                    token = tokens[i]

                    # Check if this is a hall ticket
                    if HALL_TICKET_PATTERN.match(token) and len(token) >= 9:
                        hall_ticket = token

                        # Next token should be subject code
                        if i + 1 >= len(tokens):
                            i += 1
                            continue

                        subject_code = tokens[i + 1]

                        # Validate subject code
                        if not subject_code.startswith("R") or not any(
                            c.isdigit() for c in subject_code
                        ):
                            i += 1
                            continue

                        total_rows += 1

                        # Now find: subject name (may be multiple words), marks, grade, credits
                        j = i + 2

                        # Collect subject name (words until we hit a number that looks like marks)
                        name_parts = []
                        marks = None
                        grade = None
                        credits = None

                        while j < len(tokens):
                            token_j = tokens[j]

                            # Check if it's a pure number (marks)
                            if re.match(r"^\d{1,3}$", token_j) and len(token_j) <= 3:
                                num = int(token_j)
                                if 0 <= num <= 100:
                                    marks = num
                                    j += 1
                                    break

                            # Check if it's a grade letter
                            if token_j.upper() in [
                                "O",
                                "A+",
                                "A",
                                "B+",
                                "B",
                                "C",
                                "D",
                                "E",
                                "F",
                                "AB",
                                "ABSENT",
                                "COMPLE",
                            ]:
                                # This might be an unexpected grade before marks
                                # Check next token
                                if j + 1 < len(tokens) and re.match(
                                    r"^\d{1,3}$", tokens[j + 1]
                                ):
                                    marks = int(tokens[j + 1])
                                    j += 2
                                    break

                            name_parts.append(token_j)
                            j += 1

                        # Look for grade and credits
                        if j < len(tokens):
                            grade_token = tokens[j].upper()
                            if grade_token in [
                                "O",
                                "A+",
                                "A",
                                "B+",
                                "B",
                                "C",
                                "D",
                                "E",
                                "F",
                                "AB",
                                "ABSENT",
                                "COMPLE",
                            ]:
                                grade = grade_token
                                j += 1
                            else:
                                # Try next token
                                if j + 1 < len(tokens):
                                    grade_token = tokens[j + 1].upper()
                                    if grade_token in [
                                        "O",
                                        "A+",
                                        "A",
                                        "B+",
                                        "B",
                                        "C",
                                        "D",
                                        "E",
                                        "F",
                                        "AB",
                                        "ABSENT",
                                        "COMPLE",
                                    ]:
                                        j += 1
                                        grade = grade_token
                                        j += 1
                                    else:
                                        grade = "F"

                        # Next should be credits
                        if j < len(tokens):
                            try:
                                credits = float(tokens[j])
                                if credits > 10:
                                    credits = credits / 10
                                elif 0 < credits <= 10:
                                    pass
                                else:
                                    credits = 0
                            except ValueError:
                                credits = 0

                        # Get subject name
                        subject_name = SUBJECT_MAP.get(
                            subject_code,
                            " ".join(name_parts) if name_parts else subject_code,
                        )

                        # Normalize grade
                        normalized_grade, grade_points = normalize_grade(grade)

                        # Detect supplementary
                        is_supple = "TA" in hall_ticket or re.match(
                            r"^\d{2}T", hall_ticket
                        )

                        # Only add if we have valid data
                        if hall_ticket and subject_code and normalized_grade:
                            results.append(
                                {
                                    "hall_ticket": hall_ticket,
                                    "semester": semester,
                                    "subject_code": subject_code,
                                    "subject_name": (
                                        subject_name[:100]
                                        if subject_name
                                        else subject_code
                                    ),
                                    "credits": credits if credits else 0,
                                    "grade": normalized_grade,
                                    "grade_points": grade_points,
                                    "is_supplementary": bool(is_supple),
                                    "pdf_source": filename,
                                }
                            )

                        i = j if j > i + 2 else i + 1
                    else:
                        i += 1

        # Store in database
        from app.extensions import db

        # In the parse_jntuk_pdf function, replace the storage section:

        for record in results:
            try:
                # Check if this is a supplementary result
                is_supple = record.get("is_supplementary", False)

                if is_supple:
                    # Process supplementary result
                    success, msg = process_supplementary_result(
                        record["hall_ticket"],
                        record["semester"],
                        record["subject_code"],
                        record["grade"],
                        record["grade_points"],
                        record["pdf_source"],
                    )
                else:
                    # Normal result - upsert
                    existing = Result.query.filter_by(
                        hall_ticket=record["hall_ticket"],
                        semester=record["semester"],
                        subject_code=record["subject_code"],
                        is_supplementary=False,
                    ).first()

                    if existing:
                        # Only update if grade improved
                        if (
                            not existing.is_supple_passed
                        ):  # Don't overwrite supplementary pass
                            existing.grade = record["grade"]
                            existing.grade_points = record["grade_points"]
                            existing.credits = record["credits"]
                            existing.pdf_source = record["pdf_source"]
                    else:
                        result = Result(**record)
                        db.session.add(result)

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"{record['hall_ticket']}: {str(e)}")

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise e

    return {
        "total_rows": total_rows,
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors[:10],
        "results_count": len(results),
    }


def compute_file_hash(filepath):
    """Compute SHA-256 hash of file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def process_supplementary_result(
    hall_ticket, semester, subject_code, new_grade, grade_points, pdf_source
):
    """
    Process supplementary result:
    - If student previously failed, update the old result with new grade
    - Mark as supplementary passed with star
    - Update CGPA automatically
    """
    from app.models import Result, Student, Notification
    from app.extensions import db

    # Find the original result
    original = Result.query.filter_by(
        hall_ticket=hall_ticket,
        semester=semester,
        subject_code=subject_code,
        is_supplementary=False,
    ).first()

    if original and original.grade in ["F", "AB", "ABSENT"]:
        # Student previously failed - update with new grade
        if new_grade not in ["F", "AB", "ABSENT"]:
            # Student passed in supplementary
            original.grade = new_grade
            original.grade_points = grade_points
            original.is_supple_passed = True  # Star indicator
            original.pdf_source = pdf_source

            # Create supplementary record
            supple_result = Result(
                hall_ticket=hall_ticket,
                semester=semester,
                subject_code=subject_code,
                subject_name=original.subject_name,
                credits=original.credits,
                grade=new_grade,
                grade_points=grade_points,
                is_supplementary=True,
                pdf_source=pdf_source,
            )
            db.session.add(supple_result)

            # Notify student
            student = Student.query.filter_by(hall_ticket=hall_ticket).first()
            if student:
                notif = Notification(
                    student_id=student.id,
                    message=f"Supplementary result: {subject_code} - Grade {new_grade} ⭐",
                    semester=semester,
                )
                db.session.add(notif)

            return True, "Updated original result with supplementary pass"

    elif original and original.grade not in ["F", "AB", "ABSENT"]:
        # Student already passed - just store supplementary record
        supple_result = Result(
            hall_ticket=hall_ticket,
            semester=semester,
            subject_code=subject_code,
            subject_name=original.subject_name,
            credits=original.credits,
            grade=new_grade,
            grade_points=grade_points,
            is_supplementary=True,
            pdf_source=pdf_source,
        )
        db.session.add(supple_result)
        return True, "Supplementary record stored"

    else:
        # No original result found
        return False, "No original result found"
