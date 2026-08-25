"""
Generates synthetic (fake) pilgrim document images for the OCR + rules demo.
None of this is real data — it's created purely to simulate what real
passports/visas/health certs/booking confirmations would look like as
plain-text-labeled documents, so OCR + extraction + rules can be demoed
end to end without any real pilgrim data.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(__file__), "sample_docs")
os.makedirs(OUT, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"  # monospace reads more
# reliably under OCR than the proportional font (avoids glyph-collision misreads
# like "JJ" -> ")" at small sizes)

W, H = 900, 560

def make_doc(filename, title, fields, accent=(31, 56, 100)):
    img = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 70], fill=accent)
    title_font = ImageFont.truetype(FONT_BOLD, 30)
    d.text((30, 18), title, font=title_font, fill=(255, 255, 255))

    label_font = ImageFont.truetype(FONT_BOLD, 20)
    value_font = ImageFont.truetype(FONT_REG, 20)

    y = 110
    for label, value in fields:
        d.text((40, y), f"{label}:", font=label_font, fill=(20, 20, 20))
        d.text((330, y), f"{value}", font=value_font, fill=(20, 20, 20))
        y += 48

    d.rectangle([0, 0, W - 1, H - 1], outline=(180, 180, 180), width=2)
    img.save(os.path.join(OUT, filename))
    print("wrote", filename)


# ---------- Consistent pilgrim identity used across "matching" doc sets ----------
NAME_A = "AHMED KARIM HASSAN"
DOB_A = "1985-03-14"
NAT_A = "EGYPTIAN"
PASSPORT_NO_A = "E1234567"

# ---------- 1. PASSPORTS ----------
make_doc(
    "passport_valid.png",
    "PASSPORT",
    [
        ("Full Name", NAME_A),
        ("Date of Birth", DOB_A),
        ("Nationality", NAT_A),
        ("Passport No", PASSPORT_NO_A),
        ("Issue Date", "2020-01-10"),
        ("Expiry Date", "2030-01-09"),
    ],
)

make_doc(
    "passport_expiring_soon.png",
    "PASSPORT",
    [
        ("Full Name", NAME_A),
        ("Date of Birth", DOB_A),
        ("Nationality", NAT_A),
        ("Passport No", PASSPORT_NO_A),
        ("Issue Date", "2016-02-01"),
        ("Expiry Date", "2026-11-20"),  # expires soon after a Dec 2026 trip -> violates 6-month buffer
    ],
)

# ---------- 2. VISAS ----------
make_doc(
    "visa_valid_hajj.png",
    "VISA",
    [
        ("Visa Number", "V-88213"),
        ("Holder Name", NAME_A),
        ("Visa Type", "HAJJ"),
        ("Validity Start", "2026-12-01"),
        ("Validity End", "2026-12-25"),
    ],
    accent=(46, 93, 60),
)

make_doc(
    "visa_wrong_type.png",
    "VISA",
    [
        ("Visa Number", "V-77410"),
        ("Holder Name", NAME_A),
        ("Visa Type", "TOURIST"),  # wrong type for a Hajj package -> violates Rule 2
        ("Validity Start", "2026-12-01"),
        ("Validity End", "2026-12-25"),
    ],
    accent=(46, 93, 60),
)

# ---------- 3. HEALTH CERTIFICATES ----------
make_doc(
    "health_valid.png",
    "HEALTH CERTIFICATE",
    [
        ("Holder Name", NAME_A),
        ("Vaccination", "MENINGITIS (ACWY)"),
        ("Issue Date", "2026-10-15"),
        ("Valid Until", "2029-10-15"),
    ],
    accent=(176, 42, 42),
)

make_doc(
    "health_issued_too_late.png",
    "HEALTH CERTIFICATE",
    [
        ("Holder Name", NAME_A),
        ("Vaccination", "MENINGITIS (ACWY)"),
        ("Issue Date", "2026-11-29"),  # issued 2 days before Dec 1 trip start -> violates 10-day rule
        ("Valid Until", "2029-11-29"),
    ],
    accent=(176, 42, 42),
)

# ---------- 4. BOOKING / PACKAGE CONFIRMATION ----------
make_doc(
    "booking_valid.png",
    "BOOKING CONFIRMATION",
    [
        ("Traveler Name", NAME_A),
        ("Package Type", "HAJJ"),
        ("Trip Start", "2026-12-01"),
        ("Trip End", "2026-12-25"),
        ("Hotel", "Al Kinda - Makkah"),
    ],
    accent=(31, 56, 100),
)

# ---------- 5. Name-mismatch case (for Rule 4 demo) ----------
make_doc(
    "health_name_mismatch.png",
    "HEALTH CERTIFICATE",
    [
        ("Holder Name", "AHMED KARIM HASAN"),  # subtle misspelling vs "HASSAN" -> violates Rule 4
        ("Vaccination", "MENINGITIS (ACWY)"),
        ("Issue Date", "2026-10-15"),
        ("Valid Until", "2029-10-15"),
    ],
    accent=(176, 42, 42),
)

print("All sample documents generated in:", OUT)
