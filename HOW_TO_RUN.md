# How to run this demo (Windows)

Both demos were verified end-to-end on Windows: all 4 invoice samples and all pilgrim-onboarding
samples (including the MRZ real-passport fallback) produce the documented verdicts. No code
changes were needed — the repo works as shipped.

## 1. One-time setup: install Tesseract OCR

Both demos shell out to the `tesseract` binary (not a pip package).

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

This installs to `C:\Program Files\Tesseract-OCR`. Add it to your PATH once, permanently:

```powershell
setx PATH "%PATH%;C:\Program Files\Tesseract-OCR"
```

**Open a new terminal** after running `setx` (it only affects new processes). Verify with:

```powershell
tesseract --version
```

## 2. Invoice Extraction Agent

```powershell
cd invoice_extraction_demo
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn server:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Click through all four samples from the picker:

| Sample | Expected result |
|---|---|
| Valid — hotel supplies | ✅ Auto-approve |
| Valid — F&B vendor | ✅ Auto-approve |
| Broken — total doesn't add up | ⚠️ Human review — "total doesn't match subtotal + tax" |
| Broken — missing PO number | ⚠️ Human review — "no PO number found" |

Good demo beat: show one approve, then one review with the reason called out.

## 3. Pilgrim Onboarding Agent

```powershell
cd pilgrim_onboarding_demo
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn server:app --host 127.0.0.1 --port 8001
```

Open **http://127.0.0.1:8001** (different port so it can run alongside the invoice demo).

**Process in this order** (later tabs need the booking's trip dates as context):

1. **Booking Confirmation** → `booking_valid` — sets trip dates + package type (Hajj, Dec 2026)
2. **Passport** → try `passport_valid` (✅ pass) then reset and try `passport_expiring_soon`
   (❌ fails Rule 1 — expires too close to the trip)
3. **Visa** → `visa_valid_hajj` (✅ pass) vs `visa_wrong_type` (❌ fails Rule 2 — Tourist ≠ Hajj)
4. **Health Certificate** → `health_valid` (✅ pass) vs `health_issued_too_late` (❌ fails Rule 3)
   or `health_name_mismatch` (❌ fails Rule 4, cross-document identity)
5. **Cross-Document Summary tab** — after processing booking + passport + visa + health, this
   shows the identity-consistency check and overall pass/fail/review status.

**MRZ fallback (standout feature):** upload `sample_docs/test_canada_passport.png` via the
upload box instead of picking a sample — it's a real bilingual passport whose labels the regex
parser can't read, so extraction falls back to the ICAO Machine Readable Zone. The UI's "source"
tags on each field will show `mrz` instead of `label`.

## Notes

- Each demo keeps state server-side per `session_id` (a browser tab), so refreshing the page
  starts a clean session — reset via the UI's reset button or just reload if you want a fresh run.
- No API keys, no internet access needed — everything (OCR + rules) runs locally.
- To run both demos at once for recording, just use two terminals with the two commands above
  (ports 8000 and 8001 don't conflict).
