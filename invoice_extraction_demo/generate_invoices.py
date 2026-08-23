"""
Generates synthetic (fake) vendor invoice images for the OCR + extraction demo.
None of this is real Elaf data — created purely to simulate what real vendor
invoices look like (header fields + a line-item table), so OCR + entity
extraction can be demoed end to end without any real invoice data.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(__file__), "sample_invoices")
os.makedirs(OUT, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

W, H = 950, 750


def make_invoice(filename, header, line_items, subtotal, tax, total, accent=(31, 56, 100), note=None):
    img = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 70], fill=accent)
    title_font = ImageFont.truetype(FONT_BOLD, 28)
    d.text((30, 20), "INVOICE", font=title_font, fill=(255, 255, 255))

    label_font = ImageFont.truetype(FONT_MONO_BOLD, 17)
    value_font = ImageFont.truetype(FONT_MONO, 17)

    y = 95
    for label, value in header:
        d.text((35, y), f"{label}:", font=label_font, fill=(20, 20, 20))
        d.text((260, y), f"{value}", font=value_font, fill=(20, 20, 20))
        y += 30

    # line items table
    y += 20
    table_top = y
    col_x = [35, 470, 620, 770]
    headers = ["DESCRIPTION", "QTY", "UNIT PRICE", "LINE TOTAL"]
    for cx, htext in zip(col_x, headers):
        d.text((cx, y), htext, font=label_font, fill=(255, 255, 255))
    d.rectangle([30, y - 6, W - 30, y + 24], fill=accent)
    for cx, htext in zip(col_x, headers):
        d.text((cx, y), htext, font=label_font, fill=(255, 255, 255))
    y += 34

    for desc, qty, unit_price, line_total in line_items:
        d.text((col_x[0], y), desc, font=value_font, fill=(20, 20, 20))
        d.text((col_x[1], y), str(qty), font=value_font, fill=(20, 20, 20))
        d.text((col_x[2], y), f"{unit_price:,.2f}", font=value_font, fill=(20, 20, 20))
        d.text((col_x[3], y), f"{line_total:,.2f}", font=value_font, fill=(20, 20, 20))
        y += 28

    y += 10
    d.line([30, y, W - 30, y], fill=(180, 180, 180), width=2)
    y += 16

    totals_font_lbl = ImageFont.truetype(FONT_MONO_BOLD, 18)
    totals_font_val = ImageFont.truetype(FONT_MONO, 18)
    for label, value in [("SUBTOTAL", subtotal), ("TAX (15% VAT)", tax), ("TOTAL DUE", total)]:
        d.text((620, y), f"{label}:", font=totals_font_lbl, fill=(20, 20, 20))
        d.text((790, y), f"{value:,.2f}", font=totals_font_val, fill=(20, 20, 20))
        y += 30

    if note:
        note_font = ImageFont.truetype(FONT_MONO, 14)
        d.text((35, H - 40), note, font=note_font, fill=(150, 40, 40))

    d.rectangle([0, 0, W - 1, H - 1], outline=(180, 180, 180), width=2)
    img.save(os.path.join(OUT, filename))
    print("wrote", filename)


# ---------------------------------------------------------------- INVOICE 1 ----
# Clean, everything matches (auto-approvable case)
items1 = [
    ("Bath Towels (Bulk Pack)", 50, 45.00, 2250.00),
    ("Bed Linen Sets - Queen", 30, 120.00, 3600.00),
    ("Guest Room Slippers", 200, 6.50, 1300.00),
]
subtotal1 = sum(x[3] for x in items1)
tax1 = round(subtotal1 * 0.15, 2)
total1 = round(subtotal1 + tax1, 2)
make_invoice(
    "invoice_valid_supplies.png",
    [
        ("Invoice No", "INV-2026-04417"),
        ("Vendor", "Makkah Linen & Textiles Co."),
        ("Property", "Elaf Kinda - Makkah"),
        ("PO Number", "PO-88213"),
        ("Invoice Date", "2026-09-10"),
        ("Due Date", "2026-10-10"),
    ],
    items1, subtotal1, tax1, total1,
    accent=(31, 56, 100),
)

# ---------------------------------------------------------------- INVOICE 2 ----
# F&B vendor, different property, numbers still match
items2 = [
    ("Bottled Water 500ml (Case)", 400, 8.25, 3300.00),
    ("Dates - Premium Ajwa (kg)", 150, 32.00, 4800.00),
    ("Disposable Cups (Case)", 100, 14.00, 1400.00),
]
subtotal2 = sum(x[3] for x in items2)
tax2 = round(subtotal2 * 0.15, 2)
total2 = round(subtotal2 + tax2, 2)
make_invoice(
    "invoice_valid_fnb.png",
    [
        ("Invoice No", "INV-2026-04512"),
        ("Vendor", "Jeddah Foods & Beverage Supply"),
        ("Property", "Joudyan - Jeddah"),
        ("PO Number", "PO-88377"),
        ("Invoice Date", "2026-09-14"),
        ("Due Date", "2026-10-14"),
    ],
    items2, subtotal2, tax2, total2,
    accent=(46, 93, 60),
)

# ---------------------------------------------------------------- INVOICE 3 ----
# Maintenance vendor — deliberate TOTAL MISMATCH (arithmetic doesn't add up,
# should get flagged for human review rather than auto-approved)
items3 = [
    ("HVAC Filter Replacement (Unit)", 25, 60.00, 1500.00),
    ("Plumbing Callout - Labor (hrs)", 12, 90.00, 1080.00),
]
subtotal3 = sum(x[3] for x in items3)  # 2580.00
tax3 = round(subtotal3 * 0.15, 2)      # 387.00
total3_wrong = round(subtotal3 + tax3, 2) + 150.00  # deliberately wrong total on the printed invoice
make_invoice(
    "invoice_total_mismatch.png",
    [
        ("Invoice No", "INV-2026-04588"),
        ("Vendor", "Riyadh Facilities Maintenance LLC"),
        ("Property", "Joudyan - Riyadh"),
        ("PO Number", "PO-88410"),
        ("Invoice Date", "2026-09-18"),
        ("Due Date", "2026-10-18"),
    ],
    items3, subtotal3, tax3, total3_wrong,
    accent=(192, 101, 27),
    note="(Note: this sample's printed total is intentionally wrong, to demo the 3-way/arithmetic check flagging it.)",
)

# ---------------------------------------------------------------- INVOICE 4 ----
# Missing PO number — should get flagged (can't 3-way match without a PO)
items4 = [
    ("Kitchen Cleaning Supplies (Set)", 40, 22.50, 900.00),
    ("Hand Sanitizer 1L (Case)", 60, 18.00, 1080.00),
]
subtotal4 = sum(x[3] for x in items4)
tax4 = round(subtotal4 * 0.15, 2)
total4 = round(subtotal4 + tax4, 2)
make_invoice(
    "invoice_missing_po.png",
    [
        ("Invoice No", "INV-2026-04620"),
        ("Vendor", "Madinah General Supplies"),
        ("Property", "Elaf Taiba - Madinah"),
        ("PO Number", "N/A"),
        ("Invoice Date", "2026-09-20"),
        ("Due Date", "2026-10-20"),
    ],
    items4, subtotal4, tax4, total4,
    accent=(176, 42, 42),
    note="(Note: no PO number on this invoice — cannot run a 3-way match.)",
)

print("All sample invoices generated in:", OUT)
