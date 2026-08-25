# Hospitality Group — Pilgrim Onboarding Agent

OCR → Rule-Based Validation → Human Review, demoed with synthetic pilgrim documents.

## The problem it solves

Pilgrim onboarding carries heavy paperwork — passports, visas, health certificates, booking confirmations — all checked manually at the front desk, exactly when the hotel is busiest. This demo moves validation **before arrival**: pilgrims upload documents at booking time, a rules engine validates them deterministically, and hotel check-in becomes a confirmation of a known-good status instead of a first-time document review.

## How decisions are made

Five deterministic rules — deliberately **not** AI judgments (sensitive personal documents stay local; verdicts must be exactly right and explainable):

1. **Passport validity** — expiry ≥ trip end + 6-month buffer
2. **Visa validity & type match** — window covers the trip; type matches booked package
3. **Health certificate** — issued within validity, ≥10 days before travel
4. **Cross-document identity consistency** — name/DOB/nationality match everywhere
5. **Completeness & confidence** — every required field extracted with sufficient OCR confidence

### Real-world robustness: the MRZ fallback

Real passports don't match label templates (a real bilingual passport we tested used French labels). Whenever label matching misses fields, the parser falls back to the **Machine Readable Zone** (ICAO Doc 9303) — universal across countries and layouts. Verified against a real bilingual passport image, including OCR-noise fixes (`<` padding characters, O↔0 in country codes).

Fields the OCR can't read can be entered manually in the UI — validation uses whatever is supplied.

## Run it

Requires [Tesseract OCR](https://github.com/tesseract-ocr/tesseract): `sudo apt install tesseract-ocr` (Ubuntu), `brew install tesseract` (Mac).

```bash
pip install -r requirements.txt
uvicorn server:app --reload          # → http://127.0.0.1:8000
# or: ./../run.sh onboarding  from repo root
```

Workflow to demo: process a **Booking Confirmation** first (sets trip dates/package type), then run Passport / Visa / Health samples — rules validate against the booking context. The **Cross-Document Summary** tab runs Rule 4 and computes overall status once all four are processed.

Docker:

```bash
docker build -t hospitality-onboarding .
docker run -p 8000:8000 hospitality-onboarding
```

## Files

- `server.py` — FastAPI backend with server-side sessions (cross-document rules work across tabs)
- `extraction.py` — OCR pipeline, label regex extraction, MRZ fallback parser
- `rules_engine.py` — the 5 deterministic rules
- `static/index.html` — tabbed single-page UI
- `generate_docs.py` — regenerates synthetic documents in `sample_docs/`
