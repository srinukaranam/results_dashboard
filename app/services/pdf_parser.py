"""
JNTUK Result PDF Parser - Final Working Version
"""

import pdfplumber
import re
import hashlib
from app.extensions import db
from app.models import Result, Notification, Student
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
    "R2021010": "CONSTITUTION OF INDIA",
    "R2021011": "MATHEMATICS-III",
    "R202101A": "COMMUNITY SERVICES PROJECT",
    "R2021051": "OBJECT ORIENTED PROGRAMMING THROUGH C++",
    "R2021052": "OPERATING SYSTEMS",
    "R2021053": "SOFTWARE ENGINEERING",
    "R2021054": "MATHEMATICAL FOUNDATIONS OF COMPUTER SCIENCE",
    "R2021055": "OBJECT ORIENTED PROGRAMMING THROUGH C++ LAB",
    "R2021056": "OPERATING SYSTEMS LAB",
    "R2021057": "SOFTWARE ENGINEERING LAB",
    "R2021059": "WEB APPLICATION DEVELOPMENT USING FULL STACK",
    "R2032040": "PRINCIPLES OF COMMUNICATIONS",
}

VALID_GRADES = {"A+", "A", "B", "C", "D", "E", "F", "AB", "ABSENT", "COMPLE"}

HALL_TICKET_RE = re.compile(r"^\d{2,3}[A-Z0-9]{1,4}\d{4}$")


def parse_jntuk_pdf(filepath, admin_id, filename, semester="1-1"):
    results = []
    total_rows = 0
    success_count = 0
    error_count = 0
    errors = []

    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                text = re.sub(r"\s+", " ", text)
                tokens = text.split()

                i = 0
                while i < len(tokens) - 3:
                    token = tokens[i]

                    if HALL_TICKET_RE.match(token) and len(token) >= 9:
                        hall_ticket = token

                        if i + 2 >= len(tokens):
                            i += 1
                            continue

                        subject_code = tokens[i + 1]

                        if not (
                            subject_code.startswith("R")
                            and any(c.isdigit() for c in subject_code)
                        ):
                            i += 1
                            continue

                        total_rows += 1
                        j = i + 2
                        name_parts = []
                        grade = None
                        credits = None

                        # Collect subject name parts
                        while j < len(tokens):
                            token_j = tokens[j]

                            # Check if it's a number
                            if re.match(r"^\d+\.?\d*$", token_j):
                                num = float(token_j)
                                if num <= 100 and num == int(num) and len(token_j) <= 3:
                                    # It's marks - skip it, grade comes next
                                    j += 1
                                    continue
                                elif num <= 10:
                                    # It's credits
                                    credits = num
                                    j += 1
                                    break
                                else:
                                    name_parts.append(token_j)
                                    j += 1
                                    continue

                            # Check if it's a known grade
                            if token_j.upper() in VALID_GRADES:
                                grade = token_j.upper()
                                j += 1
                                # Next should be credits
                                if j < len(tokens):
                                    try:
                                        credits = float(tokens[j])
                                        if credits > 10:
                                            credits = credits / 10
                                    except ValueError:
                                        credits = 0
                                break

                            name_parts.append(token_j)
                            j += 1

                        # Get subject name
                        subject_name = SUBJECT_MAP.get(
                            subject_code,
                            " ".join(name_parts) if name_parts else subject_code,
                        )

                        # Normalize grade
                        normalized_grade = grade if grade in GRADE_MAP else "F"
                        grade_points = GRADE_MAP.get(normalized_grade, 0)

                        # Supplementary detection
                        is_supple = bool(re.search(r"[A-Z]T[A-Z]?", hall_ticket))

                        if hall_ticket and subject_code:
                            results.append(
                                {
                                    "hall_ticket": hall_ticket,
                                    "semester": semester,
                                    "subject_code": subject_code,
                                    "subject_name": subject_name[:100],
                                    "credits": credits if credits else 0,
                                    "grade": normalized_grade,
                                    "grade_points": grade_points,
                                    "is_supplementary": is_supple,
                                    "pdf_source": filename,
                                }
                            )

                        i = j if j > i + 2 else i + 1
                    else:
                        i += 1

        # ===== STORE IN DATABASE =====
        print(f"[PARSER] Extracted {len(results)} records from PDF")

        batch = []
        for idx, record in enumerate(results):
            try:
                is_supple = record.get("is_supplementary", False)

                if is_supple:
                    # Handle supplementary
                    original = Result.query.filter_by(
                        hall_ticket=record["hall_ticket"],
                        semester=record["semester"],
                        subject_code=record["subject_code"],
                        is_supplementary=False,
                    ).first()

                    if (
                        original
                        and original.grade in ["F", "AB", "ABSENT"]
                        and record["grade"] not in ["F", "AB", "ABSENT"]
                    ):
                        original.grade = record["grade"]
                        original.grade_points = record["grade_points"]
                        original.is_supple_passed = True

                    # Create supplementary record
                    supple = Result(
                        hall_ticket=record["hall_ticket"],
                        semester=record["semester"],
                        subject_code=record["subject_code"],
                        subject_name=record.get("subject_name", ""),
                        credits=record.get("credits", 0),
                        grade=record["grade"],
                        grade_points=record["grade_points"],
                        is_supplementary=True,
                        pdf_source=record.get("pdf_source", ""),
                    )
                    db.session.add(supple)
                else:
                    # Normal result
                    existing = Result.query.filter_by(
                        hall_ticket=record["hall_ticket"],
                        semester=record["semester"],
                        subject_code=record["subject_code"],
                        is_supplementary=False,
                    ).first()

                    if existing:
                        if not existing.is_supple_passed:
                            existing.grade = record["grade"]
                            existing.grade_points = record["grade_points"]
                            existing.credits = record.get("credits", 0)
                            existing.subject_name = record.get("subject_name", "")
                            existing.pdf_source = record.get("pdf_source", "")
                    else:
                        r = Result(
                            hall_ticket=record["hall_ticket"],
                            semester=record["semester"],
                            subject_code=record["subject_code"],
                            subject_name=record.get("subject_name", ""),
                            credits=record.get("credits", 0),
                            grade=record["grade"],
                            grade_points=record["grade_points"],
                            is_supplementary=False,
                            pdf_source=record.get("pdf_source", ""),
                        )
                        db.session.add(r)

                success_count += 1

                # Commit every 100 records
                if (idx + 1) % 100 == 0:
                    db.session.commit()
                    print(f"[PARSER] Committed {idx+1}/{len(results)} records")

            except Exception as e:
                error_count += 1
                errors.append(str(e)[:100])

        # Final commit
        db.session.commit()
        print(
            f"[PARSER] Final commit done. Success: {success_count}, Errors: {error_count}"
        )

    except Exception as e:
        db.session.rollback()
        raise Exception(f"PDF parsing failed: {str(e)}")

    return {
        "total_rows": total_rows,
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors[:10],
        "results_count": len(results),
    }


def compute_file_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
