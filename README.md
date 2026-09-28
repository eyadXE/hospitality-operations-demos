# Hospitality Group — Operations AI Demos

Two production-shaped FastAPI services that automate manual document-review work for
a hospitality operator: invoice checking and pilgrim (Hajj/Umrah) onboarding
document validation. Both follow the same discipline — OCR *reads*, code *decides* —
so every approval or rejection is deterministic and explainable, never an AI guess.
Built as an operations-AI proof of concept during the Exology Pioneer Program. Full
engineering handoff: [`docs/engineering-handoff.md`](docs/engineering-handoff.md).

## 1 · The business problems

Studying how a large hospitality operator actually operates surfaced three costly pain points:

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

## Skills Demonstrated

- **OCR pipeline engineering**: local Tesseract (2× upscaling for accuracy), no cloud vision API, no data leaving the machine — a deliberate privacy-first choice for a domain (pilgrim identity documents, vendor financials) where that actually matters.
- **The "AI reads, code decides" pattern, applied consistently**: probabilistic OCR output never makes a final call — every approve/reject/route-to-human decision is a plain, testable, auditable code path (3 arithmetic/presence checks for invoices, 5 explicit rules for onboarding).
- **Real-world extraction robustness, not just happy-path parsing**: a dual extraction strategy (label-regex first, ICAO Doc 9303 Machine Readable Zone as fallback) because label-based parsing — which works fine on clean synthetic samples — breaks on real passports with non-English labels. Verified against an actual bilingual passport image, including handling MRZ-specific OCR noise (`<` padding, O↔0 confusion in country codes).
- **Stateful multi-document workflows**: server-side sessions let the onboarding demo validate a passport/visa/health-certificate/booking set together (cross-document identity consistency, visa-vs-booking package matching) rather than scoring documents in isolation.
- **Honest engineering communication**: the invoice demo's README states its real limitation (regex-based, fixed-column extraction won't generalize to arbitrary vendor layouts) instead of glossing over it — the kind of tradeoff disclosure that matters in a production handoff.
- **Deployment-ready packaging**: Dockerized, `$PORT`-aware, deployable as-is to Railway/Render/Fly.io with zero API keys required.

## Run & deploy

Each demo needs [Tesseract](https://github.com/tesseract-ocr/tesseract) (`sudo apt install tesseract-ocr`) and Python 3.10+:

```bash
cd invoice_extraction_demo && pip install -r requirements.txt && uvicorn server:app --reload
cd pilgrim_onboarding_demo && pip install -r requirements.txt && uvicorn server:app --reload
# or from repo root: ./run.sh invoice | ./run.sh onboarding
```

Windows setup + a full scripted demo walkthrough: [`HOW_TO_RUN.md`](HOW_TO_RUN.md) / [`RUN_COMMANDS.txt`](RUN_COMMANDS.txt).

Docker (Tesseract included in the image):

```bash
cd invoice_extraction_demo && docker build -t hospitality-invoice . && docker run -p 8000:8000 hospitality-invoice
cd pilgrim_onboarding_demo && docker build -t hospitality-onboarding . && docker run -p 8000:8000 hospitality-onboarding
```

No API keys needed — fully self-contained and offline-safe by design. Deployable as-is to Railway / Render / Fly.io (respects `$PORT`).

## Screenshots

*(Screenshots coming soon)*
