# Hospitality Group — Invoice Extraction Agent

OCR → Entity Extraction → Deterministic Sanity Checks, demoed with synthetic vendor invoices.

## The problem it solves

operator's 9 properties each process vendor invoices by hand: someone re-checks arithmetic, confirms a purchase order exists, and keys the data in. This demo shows the slice that matters — a machine reads the invoice locally and plain code decides, in seconds, whether it can be auto-approved or needs human review *and why*.

## How the decision works

Three deterministic checks (plain code, never an AI guess) decide **auto-approve vs human review**:

1. Line items sum to the printed subtotal (±1 cent)
2. Subtotal + tax = printed total
3. PO number present (a real 3-way match needs it)

Any single failure routes to human review with the specific reason.

## Run it

Requires [Tesseract OCR](https://github.com/tesseract-ocr/tesseract): `sudo apt install tesseract-ocr` (Ubuntu), `brew install tesseract` (Mac).

```bash
pip install -r requirements.txt
uvicorn server:app --reload          # → http://127.0.0.1:8000
# or: ./../run.sh invoice  from repo root
```

Pick one of the four sample invoices (two deliberately broken) or upload your own image. No API key needed — everything runs locally; no data leaves the machine.

Docker:

```bash
docker build -t hospitality-invoice .
docker run -p 8000:8000 hospitality-invoice
```

## Files

- `server.py` — FastAPI backend (extraction + checks endpoints)
- `invoice_extraction.py` — local Tesseract OCR pipeline + regex entity extraction
- `static/index.html` — single-page UI (sample picker, drag & drop, results)
- `generate_invoices.py` — regenerates the synthetic sample invoices in `sample_invoices/`

## Known limitation

Extraction is regex-based against a fixed-column line-item table. Real vendor invoices vary wildly in layout — production would need a layout-aware document-AI model. Stated plainly rather than glossed over.
