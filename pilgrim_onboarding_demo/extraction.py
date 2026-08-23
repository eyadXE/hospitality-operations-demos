"""
OCR + field extraction. Uses Tesseract (free, local, open-source -- no API key,
no pilgrim data ever leaves the machine) to read the document image, then two
extraction strategies fill in the structured fields:

1. Label-based regex -- matches labeled fields like "Full Name: ..." (works
   well on our synthetic sample documents, which use a fixed layout).
2. MRZ (Machine Readable Zone) parsing -- passports worldwide carry a
   standardized 2-line machine-readable zone at the bottom (ICAO Doc 9303,
   TD3 format). It's far more reliable than layout-dependent labels, since
   every passport has it in the same fixed format regardless of country,
   language, or template design. Used as a fallback whenever a passport
   field can't be found via labels -- which will be the common case for any
   real (non-synthetic) passport image, since real passports don't use our
   demo's "Full Name:" style labels.

This still mirrors the design doc: AI/OCR only *reads* the document. Neither
strategy decides anything -- that's the rules engine's job.
"""
import re
import datetime
import pytesseract
from PIL import Image

REQUIRED_FIELDS = {
    "passport": ["name", "dob", "nationality", "passport_no", "expiry_date"],
    "visa": ["name", "visa_type", "validity_start", "validity_end"],
    "health": ["name", "vaccination", "issue_date"],
    "booking": ["name", "package_type", "trip_start", "trip_end"],
}

# Each field can have multiple label variants -- real documents (especially
# bilingual ones) label fields differently than our synthetic samples do.
FIELD_LABELS = {
    "passport": {
        "name": ("Full Name", "Surname", "Nom/Surname", "Name"),
        "dob": ("Date of Birth", "Date de naissance/Date of birth", "Date of birth"),
        "nationality": ("Nationality", "Nationalite/Nationality", "Nationalité/Nationality"),
        "passport_no": ("Passport No", "Passport Nr", "Passeport N", "Passport Number"),
        "issue_date": ("Issue Date", "Date of Issue", "Date de delivrance/Date of issue"),
        "expiry_date": ("Expiry Date", "Date of Expiry", "Date d'expiration/Date of expiry"),
    },
    "visa": {
        "name": ("Holder Name",),
        "visa_type": ("Visa Type",),
        "validity_start": ("Validity Start",),
        "validity_end": ("Validity End",),
    },
    "health": {
        "name": ("Holder Name",),
        "vaccination": ("Vaccination",),
        "issue_date": ("Issue Date",),
        "valid_until": ("Valid Until",),
    },
    "booking": {
        "name": ("Traveler Name",),
        "package_type": ("Package Type",),
        "trip_start": ("Trip Start",),
        "trip_end": ("Trip End",),
        "hotel": ("Hotel",),
    },
}

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

OCR_CONFIG = "--psm 6"  # treat the document as a single uniform block of text,
# so label/value pairs on the same row are read left-to-right in order,
# rather than tesseract splitting the label column and value column into
# separate blocks and reading each top-to-bottom independently.


def run_ocr(image: Image.Image):
    """Returns (raw_text, mean_confidence 0-1).

    Runs OCR twice -- once on the image as-is, once on a preprocessed version
    (grayscale with the red channel suppressed, then auto-contrasted) -- and
    keeps whichever pass reads more actual text. The red-channel suppression
    specifically helps with red "SPECIMEN" watermarks and colored security
    patterns overlapping the text, which is a common source of OCR failure
    on passport specimens and scanned IDs."""
    w, h = image.size
    upscaled = image.resize((w * 2, h * 2), Image.LANCZOS)
    text1, conf1 = _ocr_pass(upscaled)

    preprocessed = _suppress_watermark(upscaled)
    text2, conf2 = _ocr_pass(preprocessed)

    # Prefer whichever pass produced more readable characters -- a low-noise
    # pass with less garbage text usually has a shorter, denser raw output,
    # but the simplest reliable signal is just "which one has higher mean
    # confidence AND at least as much text".
    if conf2 > conf1 and len(text2.strip()) >= len(text1.strip()) * 0.5:
        return text2, conf2
    return text1, conf1


def _ocr_pass(image: Image.Image):
    data = pytesseract.image_to_data(image, config=OCR_CONFIG, output_type=pytesseract.Output.DICT)
    text = pytesseract.image_to_string(image, config=OCR_CONFIG)
    confs = [int(c) for c in data["conf"] if c not in ("-1", -1)]
    mean_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
    return text, mean_conf


def _suppress_watermark(image: Image.Image):
    """Down-weights the red channel (where most 'SPECIMEN' watermarks and
    red security stamps live) before converting to grayscale, then
    auto-contrasts. Cheap and effective for the common case; falls back
    gracefully (just a normal grayscale conversion) if numpy isn't available."""
    try:
        import numpy as np
        from PIL import ImageOps
        arr = np.array(image.convert("RGB")).astype(float)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        gray = 0.15 * r + 0.7 * g + 0.7 * b
        gray = gray.clip(0, 255).astype("uint8")
        gray_img = Image.fromarray(gray, mode="L")
        return ImageOps.autocontrast(gray_img)
    except ImportError:
        from PIL import ImageOps
        return ImageOps.autocontrast(image.convert("L"))


# ---------------------------------------------------------------- app-screenshot guard ----
APP_SCREENSHOT_MARKERS = (
    "EXTRACTED FIELDS", "NOT FOUND", "RAW OCR TEXT", "NEEDS HUMAN REVIEW",
    "RULE 1", "RULE 2", "RULE 3", "RULE 4", "RULE 5", "COMPLETENESS & CONFIDENCE",
    "CHOOSE A SAMPLE", "UPLOAD YOUR OWN", "DOCUMENT PREVIEW",
)


def looks_like_app_screenshot(raw_text):
    """Catches the specific failure mode of someone uploading a screenshot of
    this app's own results page (instead of the underlying document image) --
    OCR then reads the app's own UI text ('Extracted fields', 'not found',
    'Rule 1 — ... NEEDS HUMAN REVIEW', etc.) mixed in with the document,
    which breaks every downstream regex. Two or more UI markers is a strong
    signal this is a screenshot of the tool, not a document."""
    text_upper = raw_text.upper()
    hits = sum(1 for marker in APP_SCREENSHOT_MARKERS if marker in text_upper)
    return hits >= 2


# ---------------------------------------------------------------- document-type sanity check ----
DOC_TYPE_KEYWORDS = {
    "passport": ("PASSPORT", "PASSEPORT"),
    "visa": ("VISA",),
    "health": ("HEALTH", "CERTIFICATE", "VACCIN"),
    "booking": ("BOOKING", "CONFIRMATION", "PACKAGE", "ITINERARY"),
}


def looks_like_expected_doc_type(doc_type, raw_text):
    """Best-effort check that the uploaded image is actually the kind of
    document the tab expects, so a pilgrim (or someone testing the demo)
    uploading the wrong document -- e.g. a college/student ID that also
    happens to have a name and a date on it -- gets caught instead of
    silently misfiled. Checks for the document-type keyword OR, for
    passports specifically, a valid-looking MRZ line (some real passports
    render 'PASSPORT' in a font/language OCR won't catch cleanly, but the
    MRZ format itself is a strong signal on its own)."""
    text_upper = raw_text.upper()
    keywords = DOC_TYPE_KEYWORDS.get(doc_type, ())
    if any(kw in text_upper for kw in keywords):
        return True
    if doc_type == "passport":
        for line in raw_text.splitlines():
            cleaned = line.strip().upper().replace(" ", "")
            if cleaned.startswith("P<") and len(cleaned) > 15:
                return True
    return False


# ---------------------------------------------------------------- MRZ parsing ----
MRZ_LINE2_RE = re.compile(r"([A-Z0-9<]{6,12})\d?([A-Z0-9]{3})(\d{6})\d[MF<](\d{6})")
STANDALONE_PASSPORT_NO_RE = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")


def _is_noise_token(token):
    """MRZ filler ('<' chevrons) sometimes gets OCR'd as repeated letters or
    digit/letter soup (e.g. a run of '<' misread as 'KKKKKKK' or
    '666666KKKKKKKKK'). A token that's mostly one repeated character, too
    short to be a real name, or long with no vowel at all (real names
    virtually always have one) is filler noise, not a name."""
    if len(token) < 2:
        return True
    from collections import Counter
    most_common_count = Counter(token).most_common(1)[0][1]
    if (most_common_count / len(token)) > 0.5:
        return True
    if len(token) > 8 and not any(v in token for v in "AEIOU"):
        return True
    return False


def _clean_name_tokens(text):
    """Keeps tokens until the first one that looks like OCR-misread filler."""
    kept = []
    for token in text.split():
        if _is_noise_token(token):
            break
        kept.append(token)
    return " ".join(kept)


def _mrz_date(yymmdd, is_dob):
    """Convert MRZ's 2-digit-year date into YYYY-MM-DD. DOB is always in the
    past, so a 2-digit year greater than the current 2-digit year implies the
    1900s; expiry dates are assumed 2000s (passports issued that old aren't
    still in use)."""
    yy, mm, dd = int(yymmdd[0:2]), yymmdd[2:4], yymmdd[4:6]
    if is_dob:
        current_yy = datetime.date.today().year % 100
        century = 1900 if yy > current_yy else 2000
    else:
        century = 2000
    try:
        return f"{century + yy:04d}-{mm}-{dd}"
    except Exception:
        return None


def extract_from_mrz(raw_text):
    """Finds and parses a TD3-format passport MRZ (2 lines of ~44 chars) from
    noisy OCR text. Returns a dict of whatever fields it could confidently
    parse -- empty dict if no MRZ-shaped line is found."""
    result = {}
    lines = [l.strip().upper().replace(" ", "") for l in raw_text.splitlines()]

    # Line 1: P<CCCSURNAME<<GIVENNAMES<<<<...
    name_line = next((l for l in lines if l.startswith("P<") and len(l) > 15), None)
    if name_line:
        body = name_line[5:]  # skip "P<" + 3-letter country code
        parts = body.split("<<", 1)
        if len(parts) == 2:
            surname = _clean_name_tokens(parts[0].replace("<", " ").strip())
            given = _clean_name_tokens(parts[1].replace("<", " ").strip())
            if surname:
                result["name"] = f"{surname} {given}".strip()

    # Line 2: passport_no + check + nationality(3) + DOB(6) + check + sex + expiry(6) + ...
    for l in lines:
        m = MRZ_LINE2_RE.search(l)
        if m:
            # OCR sometimes reads the letter 'O' as digit '0' inside the
            # 3-letter country code — normalize it back.
            nationality = m.group(2).replace("0", "O")
            if not nationality.isalpha():
                continue  # not a real country code, likely a false match
            dob_raw, exp_raw = m.group(3), m.group(4)
            result["nationality"] = nationality
            dob = _mrz_date(dob_raw, is_dob=True)
            exp = _mrz_date(exp_raw, is_dob=False)
            if dob:
                result["dob"] = dob
            if exp:
                result["expiry_date"] = exp
            break

    return result


def _fallback_passport_number(raw_text):
    """Best-effort: look for a standalone alphanumeric token shaped like a
    passport number (e.g. 'PP3000000') printed on the document, used when
    neither the label match nor the MRZ capture a clean number."""
    for token in STANDALONE_PASSPORT_NO_RE.findall(raw_text):
        return token
    return None


def extract_fields(doc_type: str, raw_text: str, ocr_confidence: float):
    """Regex-parses OCR text into a structured field dict for the given doc type.
    For passports, falls back to MRZ parsing for any field the label match missed."""
    labels = FIELD_LABELS[doc_type]
    result = {}
    field_source = {}
    lines = raw_text.splitlines()

    for field_key, label_variants in labels.items():
        value = None
        for label in label_variants:
            # \b...\b enforces whole-word/phrase matching so a label like "Name"
            # doesn't false-positive match inside an unrelated word like "Given
            # NAMES" -- without this, a bad partial match blocks the MRZ
            # fallback below (it only kicks in when the label match found
            # nothing at all, not when it found something wrong).
            pattern = re.compile(r"\b" + re.escape(label) + r"\b" + r"\s*:?\s*(.+)", re.IGNORECASE)
            for line in lines:
                m = pattern.search(line)
                if m:
                    candidate = m.group(1).strip(" :\\'\"")
                    # Reject candidates that are mostly punctuation/noise --
                    # a real field value should have at least 2 alphanumeric chars.
                    if candidate and sum(c.isalnum() for c in candidate) >= 2:
                        value = candidate
                        break
            if value:
                break
        if value:
            field_source[field_key] = "label"
        result[field_key] = value

    if doc_type == "passport":
        mrz_fields = extract_from_mrz(raw_text)
        for key, val in mrz_fields.items():
            if not result.get(key):
                result[key] = val
                field_source[key] = "mrz"
        if not result.get("passport_no"):
            fallback = _fallback_passport_number(raw_text)
            if fallback:
                result["passport_no"] = fallback
                field_source["passport_no"] = "fallback"

    result["_ocr_confidence"] = ocr_confidence
    result["_raw_text"] = raw_text
    result["_field_source"] = field_source
    return result
