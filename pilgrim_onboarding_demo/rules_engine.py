"""
Deterministic rules engine for pilgrim document validation.
No AI/LLM makes the pass/fail decision here — plain, explainable code only.
"""
from datetime import datetime, timedelta

DATE_FMT = "%Y-%m-%d"


def _parse(d):
    if not d:
        return None
    try:
        return datetime.strptime(d.strip(), DATE_FMT)
    except ValueError:
        return None


def check_passport_validity(passport, trip, buffer_months=6):
    """Rule 1: passport must be valid at least `buffer_months` beyond trip end date."""
    expiry = _parse(passport.get("expiry_date"))
    trip_end = _parse(trip.get("trip_end"))
    if not expiry or not trip_end:
        return "review", "Could not read passport expiry date or trip end date clearly."
    min_required = trip_end + timedelta(days=30 * buffer_months)
    if expiry < min_required:
        return "fail", (
            f"Passport expires {expiry.strftime(DATE_FMT)}, which is less than "
            f"{buffer_months} months after the trip end date ({trip_end.strftime(DATE_FMT)}). "
            f"Please renew your passport before uploading again."
        )
    return "pass", "Passport valid well beyond the trip dates."


def check_visa_validity_and_type(visa, trip):
    """Rule 2: visa not expired, covers trip dates, and type matches package type."""
    start = _parse(visa.get("validity_start"))
    end = _parse(visa.get("validity_end"))
    trip_start = _parse(trip.get("trip_start"))
    trip_end = _parse(trip.get("trip_end"))
    if not all([start, end, trip_start, trip_end]):
        return "review", "Could not read visa or trip dates clearly."

    if start > trip_start or end < trip_end:
        return "fail", (
            f"Visa validity ({start.strftime(DATE_FMT)} to {end.strftime(DATE_FMT)}) does not "
            f"fully cover the trip dates ({trip_start.strftime(DATE_FMT)} to {trip_end.strftime(DATE_FMT)})."
        )

    visa_type = (visa.get("visa_type") or "").strip().upper()
    package_type = (trip.get("package_type") or "").strip().upper()
    if visa_type and package_type and visa_type != package_type:
        return "fail", (
            f"Visa type is '{visa_type}' but the booked package is '{package_type}'. "
            f"Visa type must match the package type."
        )
    return "pass", "Visa is valid, covers the trip dates, and matches the package type."


def check_health_certificate(health, trip, min_days_before=10, validity_years=3):
    """Rule 3: vaccination present, issued within validity window and at least
    `min_days_before` days before travel."""
    issue = _parse(health.get("issue_date"))
    trip_start = _parse(trip.get("trip_start"))
    vaccination = (health.get("vaccination") or "").strip()

    if not vaccination:
        return "fail", "No vaccination record found on the health certificate."
    if not issue or not trip_start:
        return "review", "Could not read the health certificate issue date or trip start date clearly."

    days_before_travel = (trip_start - issue).days
    if days_before_travel < min_days_before:
        return "fail", (
            f"Health certificate was issued on {issue.strftime(DATE_FMT)}, only "
            f"{max(days_before_travel, 0)} day(s) before travel. It must be issued at least "
            f"{min_days_before} days before travel to take effect."
        )

    max_age = timedelta(days=365 * validity_years)
    if trip_start - issue > max_age:
        return "fail", (
            f"Health certificate was issued on {issue.strftime(DATE_FMT)}, which is more than "
            f"{validity_years} years before travel and is no longer valid."
        )
    return "pass", f"Vaccination ({vaccination}) present and certificate is within its validity window."


def _normalize_name(name):
    return " ".join((name or "").strip().upper().split())


def check_identity_consistency(documents):
    """Rule 4: name must match exactly (after normalization) across all provided documents."""
    names = {}
    for doc_type, fields in documents.items():
        name = fields.get("name")
        if name:
            names[doc_type] = _normalize_name(name)

    if len(names) < 2:
        return "review", "Not enough documents uploaded yet to cross-check identity."

    unique_names = set(names.values())
    if len(unique_names) == 1:
        return "pass", "Name matches exactly across all uploaded documents."

    detail = ", ".join(f"{doc}: '{val}'" for doc, val in names.items())
    return "fail", f"Name mismatch across documents — {detail}. Please check spelling and re-upload."


def check_completeness_and_confidence(extracted_fields, required_fields, min_confidence=0.6):
    """Rule 5: every required field extracted, and OCR confidence above threshold."""
    missing = [f for f in required_fields if not extracted_fields.get(f)]
    if missing:
        return "fail", f"Missing or unreadable field(s): {', '.join(missing)}. Please upload a clearer document."
    conf = extracted_fields.get("_ocr_confidence", 1.0)
    if conf < min_confidence:
        return "review", f"OCR confidence is low ({conf:.0%}). Routed for human review rather than a guess."
    return "pass", f"All required fields extracted with acceptable confidence ({conf:.0%})."
