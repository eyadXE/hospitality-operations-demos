"""FastAPI backend serving the Pilgrim Onboarding demo UI.

Server-side sessions hold processed documents so the cross-document rules
(identity consistency, overall status) work exactly like the original app.
"""
import hashlib
import io
import os
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from extraction import (
    REQUIRED_FIELDS,
    extract_fields,
    looks_like_app_screenshot,
    looks_like_expected_doc_type,
    run_ocr,
)
from rules_engine import (
    check_completeness_and_confidence,
    check_health_certificate,
    check_identity_consistency,
    check_passport_validity,
    check_visa_validity_and_type,
)

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")

SAMPLES = {
    "passport": [
        {"id": "passport_valid", "file": "passport_valid.png", "label": "Valid passport"},
        {"id": "passport_expiring_soon", "file": "passport_expiring_soon.png",
         "label": "Expiring too soon (violates Rule 1)"},
    ],
    "visa": [
        {"id": "visa_valid_hajj", "file": "visa_valid_hajj.png", "label": "Valid Hajj visa"},
        {"id": "visa_wrong_type", "file": "visa_wrong_type.png",
         "label": "Wrong type — Tourist instead of Hajj (violates Rule 2)"},
    ],
    "health": [
        {"id": "health_valid", "file": "health_valid.png", "label": "Valid health certificate"},
        {"id": "health_issued_too_late", "file": "health_issued_too_late.png",
         "label": "Issued too close to travel (violates Rule 3)"},
        {"id": "health_name_mismatch", "file": "health_name_mismatch.png",
         "label": "Name mismatch vs passport (violates Rule 4)"},
    ],
    "booking": [
        {"id": "booking_valid", "file": "booking_valid.png", "label": "Valid Hajj booking"},
    ],
}

DOC_LABELS = {
    "passport": "passport",
    "visa": "visa",
    "health": "health certificate",
    "booking": "booking confirmation",
}

FIELD_DISPLAY = {
    "passport": {"name": "Full Name", "dob": "Date of Birth", "nationality": "Nationality",
                 "passport_no": "Passport Number", "issue_date": "Issue Date", "expiry_date": "Expiry Date"},
    "visa": {"name": "Holder Name", "visa_type": "Visa Type",
             "validity_start": "Validity Start", "validity_end": "Validity End"},
    "health": {"name": "Holder Name", "vaccination": "Vaccination",
               "issue_date": "Issue Date", "valid_until": "Valid Until"},
    "booking": {"name": "Traveler Name", "package_type": "Package Type",
                "trip_start": "Trip Start", "trip_end": "Trip End", "hotel": "Hotel"},
}

app = FastAPI(title="Elaf Group — Pilgrim Onboarding Agent")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# session_id -> {"docs": {type: fields}, "ocr_cache": {(type, hash): (text, conf)}}
SESSIONS: dict[str, dict] = {}


def _session(session_id: str) -> dict:
    return SESSIONS.setdefault(session_id, {"docs": {}, "ocr_cache": {}})


@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.get("/api/meta")
def meta():
    return {
        "samples": SAMPLES,
        "fields": FIELD_DISPLAY,
        "required": REQUIRED_FIELDS,
        "doc_labels": DOC_LABELS,
    }


@app.get("/api/sample-image/{sample_id}")
def sample_image(sample_id: str):
    for docs in SAMPLES.values():
        for s in docs:
            if s["id"] == sample_id:
                return FileResponse(os.path.join(SAMPLE_DIR, s["file"]))
    raise HTTPException(404, "Unknown sample")


def _process(session_id: str, doc_type: str, image: Image.Image) -> dict:
    sess = _session(session_id)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    key = (doc_type, hashlib.md5(buf.getvalue()).hexdigest())
    if key not in sess["ocr_cache"]:
        sess["ocr_cache"][key] = run_ocr(image)
    raw_text, conf = sess["ocr_cache"][key]
    fields = extract_fields(doc_type, raw_text, conf)
    sess["docs"][doc_type] = fields
    return {
        "fields": {k: v for k, v in fields.items() if not k.startswith("_")},
        "sources": fields.get("_field_source", {}),
        "ocr_confidence": fields.get("_ocr_confidence"),
        "raw_text": raw_text,
        "is_screenshot": looks_like_app_screenshot(raw_text),
        "doc_type_ok": looks_like_expected_doc_type(doc_type, raw_text),
        "missing": [k for k, v in fields.items() if not k.startswith("_") and not v],
    }


@app.post("/api/process-sample/{doc_type}/{sample_id}")
def process_sample(doc_type: str, sample_id: str, session_id: str = Form(...)):
    path = next((os.path.join(SAMPLE_DIR, s["file"])
                 for s in SAMPLES.get(doc_type, []) if s["id"] == sample_id), None)
    if not path:
        raise HTTPException(404, "Unknown sample")
    image = Image.open(path).convert("RGB")
    return _process(session_id, doc_type, image)


@app.post("/api/process-upload/{doc_type}")
def process_upload(doc_type: str, session_id: str = Form(...), file: UploadFile = File(...)):
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(400, "Please upload a PNG or JPG image.")
    try:
        image = Image.open(file.file).convert("RGB")
    except Exception:
        raise HTTPException(400, "Could not read that image file.")
    return _process(session_id, doc_type, image)


class ManualFields(dict):
    pass


@app.post("/api/set-manual/{doc_type}")
async def set_manual(doc_type: str, request: dict):
    session_id = request.get("session_id", "")
    values: dict = request.get("values", {})
    sess = _session(session_id)
    if doc_type not in sess["docs"]:
        raise HTTPException(400, "Process a document first.")
    fields = sess["docs"][doc_type]
    for k, v in values.items():
        if v and v.strip():
            fields[k] = v.strip()
            fields.setdefault("_field_source", {})[k] = "manual"
    return {"ok": True}


def _trip(sess):
    booking = sess["docs"].get("booking")
    if not booking:
        return None
    return {"trip_start": booking.get("trip_start"),
            "trip_end": booking.get("trip_end"),
            "package_type": booking.get("package_type")}


@app.get("/api/evaluate/{doc_type}")
def evaluate(doc_type: str, session_id: str):
    """Runs every rule applicable to one document type against the current session."""
    sess = _session(session_id)
    if doc_type not in sess["docs"]:
        raise HTTPException(400, "No document processed for this type.")
    fields = sess["docs"][doc_type]
    trip = _trip(sess)
    verdicts = []

    def add(rule, status, msg):
        verdicts.append({"rule": rule, "status": status, "message": msg})

    no_ctx = "Upload the Booking Confirmation too, so trip dates are known and this rule can run."
    if doc_type == "passport":
        add("Rule 1 — Passport Validity",
            *(check_passport_validity(fields, trip) if trip else ("review", no_ctx)))
    elif doc_type == "visa":
        add("Rule 2 — Visa Validity & Type Match",
            *(check_visa_validity_and_type(fields, trip) if trip else ("review", no_ctx)))
    elif doc_type == "health":
        add("Rule 3 — Health Certificate Validity",
            *(check_health_certificate(fields, trip) if trip else ("review", no_ctx)))
    add(f"Rule 5 — Completeness & Confidence",
        *check_completeness_and_confidence(fields, REQUIRED_FIELDS[doc_type]))
    return {"verdicts": verdicts}


@app.get("/api/summary")
def summary(session_id: str):
    sess = _session(session_id)
    docs = sess["docs"]
    out = {"processed": list(docs.keys()), "identity": None, "overall": None}

    if len(docs) >= 2:
        status, msg = check_identity_consistency(docs)
        out["identity"] = {"status": status, "message": msg}

    if len(docs) == 4:
        trip = _trip(sess)
        results = []
        if "passport" in docs and trip:
            results.append(check_passport_validity(docs["passport"], trip)[0])
        if "visa" in docs and trip:
            results.append(check_visa_validity_and_type(docs["visa"], trip)[0])
        if "health" in docs and trip:
            results.append(check_health_certificate(docs["health"], trip)[0])
        results.append(check_identity_consistency(docs)[0])
        for dt in docs:
            results.append(check_completeness_and_confidence(docs[dt], REQUIRED_FIELDS[dt])[0])
        if "fail" in results:
            out["overall"] = {"status": "fail",
                              "message": "One or more rules were violated. Pilgrim has been notified with specific reasons."}
        elif "review" in results:
            out["overall"] = {"status": "review",
                              "message": "Routed to a human reviewer (low confidence or missing trip context)."}
        else:
            out["overall"] = {"status": "pass",
                              "message": "All rules passed. At the hotel, reception only confirms this status — "
                                         "no re-checking documents from scratch."}
    return out


@app.post("/api/reset")
def reset(request: dict):
    SESSIONS.pop(request.get("session_id", ""), None)
    return {"ok": True}


def new_session() -> str:
    return uuid.uuid4().hex[:12]
