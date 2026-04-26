"""
CGPA Calculator for JNTUK R20/R19 Grading System

Grade Points:
O = 10, A+ = 9, A = 8, B+ = 7, B = 6, C = 5, D = 4, E = 3, F = 0, AB = 0
"""

from app.extensions import db
from app.models import Result

# JNTUK Grade to Points mapping
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

# All semesters in order
ALL_SEMESTERS = ["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2"]
YEAR_MAP = {
    "1": ["1-1", "1-2"],
    "2": ["2-1", "2-2"],
    "3": ["3-1", "3-2"],
    "4": ["4-1", "4-2"],
}


def calculate_sgpa(hall_ticket, semester):
    """
    Calculate SGPA for a specific semester.
    SGPA = Σ(Credit × Grade Points) / Σ Credits
    """
    results = Result.query.filter_by(
        hall_ticket=hall_ticket,
        semester=semester,
        is_supplementary=False,  # Exclude supplementary for main calculation
    ).all()

    if not results:
        return None, 0, 0

    total_credits = 0
    total_grade_points = 0

    for result in results:
        credits = float(result.credits) if result.credits else 0
        grade_pts = float(result.grade_points) if result.grade_points else 0

        # Skip subjects with 0 credits or where grade is COMPLE
        if result.grade == "COMPLE":
            continue

        total_credits += credits
        total_grade_points += credits * grade_pts

    if total_credits == 0:
        return None, 0, 0

    sgpa = round(total_grade_points / total_credits, 2)
    return sgpa, total_credits, total_grade_points


def calculate_cgpa(hall_ticket, up_to_semester=None):
    """
    Calculate CGPA up to a specific semester.
    CGPA = Σ(Credit × Grade Points across all sems) / Σ Total Credits
    """
    if up_to_semester:
        sem_index = ALL_SEMESTERS.index(up_to_semester) + 1
        semesters = ALL_SEMESTERS[:sem_index]
    else:
        semesters = ALL_SEMESTERS

    results = Result.query.filter(
        Result.hall_ticket == hall_ticket,
        Result.semester.in_(semesters),
        Result.is_supplementary == False,
    ).all()

    if not results:
        return None, 0, 0

    total_credits = 0
    total_grade_points = 0

    for result in results:
        credits = float(result.credits) if result.credits else 0
        grade_pts = float(result.grade_points) if result.grade_points else 0

        if result.grade == "COMPLE":
            continue

        total_credits += credits
        total_grade_points += credits * grade_pts

    if total_credits == 0:
        return None, 0, 0

    cgpa = round(total_grade_points / total_credits, 2)
    return cgpa, total_credits, total_grade_points


def get_year_results(hall_ticket, year):
    """
    Get combined results for an academic year (2 semesters).
    Returns list of results + year CGPA.
    """
    semesters = YEAR_MAP.get(str(year), [])
    if not semesters:
        return None, None

    results = (
        Result.query.filter(
            Result.hall_ticket == hall_ticket,
            Result.semester.in_(semesters),
            Result.is_supplementary == False,
        )
        .order_by(Result.semester, Result.subject_code)
        .all()
    )

    if not results:
        return None, None

    # Calculate year CGPA
    total_credits = 0
    total_grade_points = 0

    for r in results:
        credits = float(r.credits) if r.credits else 0
        grade_pts = float(r.grade_points) if r.grade_points else 0
        if r.grade != "COMPLE":
            total_credits += credits
            total_grade_points += credits * grade_pts

    year_cgpa = (
        round(total_grade_points / total_credits, 2) if total_credits > 0 else None
    )

    return results, year_cgpa


def get_semester_results(hall_ticket, semester):
    """Get results for a specific semester."""
    return (
        Result.query.filter_by(
            hall_ticket=hall_ticket, semester=semester, is_supplementary=False
        )
        .order_by(Result.subject_code)
        .all()
    )


def get_supplementary_results(hall_ticket):
    """Get supplementary results for a student."""
    return (
        Result.query.filter_by(hall_ticket=hall_ticket, is_supplementary=True)
        .order_by(Result.semester, Result.subject_code)
        .all()
    )


def get_weak_subjects(hall_ticket):
    """
    Identify weak subjects (grade C or below, or F).
    Returns list of subjects with grade ≤ C.
    """
    weak_grades = ["C", "D", "E", "F", "AB", "ABSENT"]

    results = (
        Result.query.filter(
            Result.hall_ticket == hall_ticket,
            Result.grade.in_(weak_grades),
            Result.is_supplementary == False,
        )
        .order_by(Result.semester)
        .all()
    )

    return results


def get_backlog_count(hall_ticket):
    """Count active backlogs (F/AB grades not cleared in supplementary)."""
    # Get all regular results with F or AB
    failed = Result.query.filter(
        Result.hall_ticket == hall_ticket,
        Result.grade.in_(["F", "AB", "ABSENT"]),
        Result.is_supplementary == False,
    ).all()

    backlog_count = 0
    for f in failed:
        # Check if cleared in supplementary
        cleared = Result.query.filter_by(
            hall_ticket=hall_ticket,
            semester=f.semester,
            subject_code=f.subject_code,
            is_supplementary=True,
        ).first()

        if not cleared or cleared.grade in ["F", "AB", "ABSENT"]:
            backlog_count += 1

    return backlog_count


def get_completed_semesters(hall_ticket):
    """Get list of semesters that have results."""
    results = (
        Result.query.filter_by(hall_ticket=hall_ticket).distinct(Result.semester).all()
    )
    semesters = list(set(r.semester for r in results))
    semesters.sort()
    return semesters
