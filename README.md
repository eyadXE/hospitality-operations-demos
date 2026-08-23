# Elaf Group — Operations AI Demos

Two working proof-of-concept demos plus an operational playbook, built for **Elaf Group** (Saudi hospitality operator, 9 properties) during the **Exology Pioneer Program client challenge**. Full engineering handoff: [`docs/engineering-handoff.md`](docs/engineering-handoff.md).

## 1 · The business problems

Studying how Elaf actually operates surfaced three costly pain points:

- **Invoices are processed by hand — nine times over.** Each property processes its own vendor invoices manually, with no central visibility. Every invoice requires someone to check the arithmetic, confirm a purchase order exists, and key the data in — slow, error-prone, and impossible to consolidate for reporting.
- **Pilgrim onboarding drowns in paperwork at the worst possible moment.** Passports, visas, health certificates and booking confirmations are checked *manually at the front desk* — exactly when the hotel is busiest during Hajj season. A document problem discovered at check-in means a distressed guest and an unfixable booking.
- **Demand swings violently with a moving calendar.** Hajj shifts ~11 days earlier every Gregorian year (lunar Hijri calendar), so staffing and procurement plans tied to fixed months go stale annually. Staffing via Saudi's Ajeer platform, procurement lead times, and safety stock all need to key off the *Hijri* calendar, not guesswork.

## 2 · How these products solve it

**Invoice Extraction Agent** ([`invoice_extraction_demo/`](invoice_extraction_demo/)) — upload or pick an invoice image; local OCR reads it, entities are extracted (header fields, line items, totals), and three deterministic checks decide instantly: line items sum to subtotal · subtotal + tax = total · PO number present. All pass → **auto-approve**; any failure → **route to human review with the specific reason**. Verified against 4 synthetic invoices including 2 deliberately broken cases.

**Pilgrim Onboarding Agent** ([`pilgrim_onboarding_demo/`](pilgrim_onboarding_demo/)) — validates documents *before the pilgrim travels*, so hotel check-in becomes a confirmation instead of a first-time document review. Five deterministic rules cover passport validity (+6-month buffer), visa type/date match vs the booked package, health-certificate timing, cross-document identity consistency, and extraction confidence. A **Machine Readable Zone (MRZ) fallback** parses real-world passports regardless of country or layout — label templates fail on real bilingual passports; the ICAO-standard MRZ never does. Tested on a real bilingual passport image.

**Seasonal Demand Response Plan** ([`docs/seasonal-demand-response-plan.md`](docs/seasonal-demand-response-plan.md)) — deliberately a playbook, not a forecasting model: three demand tiers keyed to the Hijri calendar, six-phase staffing plan (Ajeer registration → peak rotations), six-phase procurement plan (dual-sourcing → centralized peak ordering).

### The shared design principle

Wherever a decision affects a person or a payment, the AI/OCR component **only reads data — plain, auditable code makes every pass/fail call**. And everything runs locally (Tesseract OCR): no pilgrim or invoice data is ever sent to a third-party API.

## 3 · Tech & architecture

```
image ──► Tesseract OCR (local, upscaled 2×)
            ├─► regex entity extraction (+ MRZ fallback for passports)
            └─► FastAPI backend ──► deterministic rules engine
                     │                 (sanity checks / 5 validation rules)
                     ▼
              single-page web UI — verdicts, extracted fields,
              manual-entry fallback for unread fields, cross-doc summary
```

| | Invoice demo | Onboarding demo |
|---|---|---|
| Backend | `server.py` (FastAPI) | `server.py` (FastAPI + server-side sessions) |
| Extraction | `invoice_extraction.py` | `extraction.py` (label regex + MRZ parser) |
| Decisions | 3 arithmetic/presence checks | `rules_engine.py` (5 rules) |

## Run & deploy

Each demo needs [Tesseract](https://github.com/tesseract-ocr/tesseract) (`sudo apt install tesseract-ocr`) and Python 3.10+:

```bash
cd invoice_extraction_demo && pip install -r requirements.txt && uvicorn server:app --reload
cd pilgrim_onboarding_demo && pip install -r requirements.txt && uvicorn server:app --reload
# or from repo root: ./run.sh invoice | ./run.sh onboarding
```

Docker (Tesseract included in the image):

```bash
cd invoice_extraction_demo && docker build -t elaf-invoice . && docker run -p 8000:8000 elaf-invoice
cd pilgrim_onboarding_demo && docker build -t elaf-onboarding . && docker run -p 8000:8000 elaf-onboarding
```

No API keys needed — fully self-contained and offline-safe by design. Deployable as-is to Railway / Render / Fly.io (respects `$PORT`).

## Skills demonstrated

OCR pipelines · information/extraction engineering · deterministic decision systems over probabilistic AI · privacy-first architecture · MRZ parsing (ICAO Doc 9303) · client-facing demo craft · operational planning under calendar uncertainty.
