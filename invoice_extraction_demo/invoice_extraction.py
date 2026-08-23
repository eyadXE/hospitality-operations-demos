"""
OCR + entity extraction for vendor invoices. Same principle as the pilgrim
onboarding demo: Tesseract (free, local, open-source) reads the document;
plain code extracts structured entities from the OCR text. No AI model
decides anything here — that's a job for a rules/matching layer downstream
(3-way match against PO, arithmetic check), not this module.

Extracts two kinds of entities:
1. Header fields — invoice number, vendor, property, PO number, dates.
2. Line items — description, quantity, unit price, line total — read out of
   the invoice's item table.
"""
import re
import pytesseract
from PIL import Image

OCR_CONFIG = "--psm 6"

HEADER_LABELS = {
    "invoice_no": ("Invoice No",),
    "vendor": ("Vendor",),
    "property": ("Property",),
    "po_number": ("PO Number",),
    "invoice_date": ("Invoice Date",),
    "due_date": ("Due Date",),
}

TOTALS_LABELS = {
    "subtotal": ("SUBTOTAL",),
    "tax": ("TAX",),
    "total": ("TOTAL DUE",),
}

# A line-item row: description text, then a run of numeric columns
# (qty, unit price, line total) separated by whitespace.
LINE_ITEM_RE = re.compile(
    r"^(?P<desc>.+?)\s+(?P<qty>\d+)\s+(?P<unit_price>[\d,]+\.\d{2})\s+(?P<line_total>[\d,]+\.\d{2})\s*$"
)
MONEY_RE = re.compile(r"[\d,]+\.\d{2}")


def run_ocr(image: Image.Image):
    w, h = image.size
    image = image.resize((w * 2, h * 2), Image.LANCZOS)
    data = pytesseract.image_to_data(image, config=OCR_CONFIG, output_type=pytesseract.Output.DICT)
    text = pytesseract.image_to_string(image, config=OCR_CONFIG)
    confs = [int(c) for c in data["conf"] if c not in ("-1", -1)]
    mean_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
    return text, mean_conf


def _to_float(s):
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def extract_header(raw_text):
    lines = raw_text.splitlines()
    result = {}
    for field_key, label_variants in HEADER_LABELS.items():
        value = None
        for label in label_variants:
            pattern = re.compile(re.escape(label) + r"\s*:?\s*(.+)", re.IGNORECASE)
            for line in lines:
                m = pattern.search(line)
                if m:
                    candidate = m.group(1).strip()
                    if candidate:
                        value = candidate
                        break
            if value:
                break
        result[field_key] = value
    return result


def extract_totals(raw_text):
    lines = raw_text.splitlines()
    result = {}
    for field_key, label_variants in TOTALS_LABELS.items():
        value = None
        for label in label_variants:
            pattern = re.compile(re.escape(label) + r".*?([\d,]+\.\d{2})\s*$", re.IGNORECASE)
            for line in lines:
                m = pattern.search(line)
                if m:
                    value = _to_float(m.group(1))
                    break
            if value is not None:
                break
        result[field_key] = value
    return result


def extract_line_items(raw_text):
    """Parses each line-item row: description + qty + unit price + line total.
    Skips header/total rows automatically since they don't match the 4-column
    numeric pattern."""
    items = []
    for line in raw_text.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        m = LINE_ITEM_RE.match(line)
        if m:
            desc = m.group("desc").strip()
            if desc.upper() in ("DESCRIPTION",):
                continue
            items.append({
                "description": desc,
                "qty": int(m.group("qty")),
                "unit_price": _to_float(m.group("unit_price")),
                "line_total": _to_float(m.group("line_total")),
            })
    return items


def extract_invoice(raw_text, ocr_confidence):
    header = extract_header(raw_text)
    totals = extract_totals(raw_text)
    line_items = extract_line_items(raw_text)

    # Sanity checks — plain arithmetic, not AI: does the extracted data add up?
    computed_subtotal = round(sum(i["line_total"] for i in line_items if i["line_total"]), 2) if line_items else None
    checks = {}
    if computed_subtotal is not None and totals.get("subtotal") is not None:
        checks["subtotal_matches_line_items"] = abs(computed_subtotal - totals["subtotal"]) < 0.01
    if totals.get("subtotal") is not None and totals.get("tax") is not None and totals.get("total") is not None:
        expected_total = round(totals["subtotal"] + totals["tax"], 2)
        checks["total_matches_subtotal_plus_tax"] = abs(expected_total - totals["total"]) < 0.01
    checks["has_po_number"] = bool(header.get("po_number")) and header.get("po_number", "").upper() not in ("N/A", "NONE", "")

    return {
        "header": header,
        "line_items": line_items,
        "totals": totals,
        "computed_subtotal": computed_subtotal,
        "checks": checks,
        "ocr_confidence": ocr_confidence,
        "raw_text": raw_text,
    }
