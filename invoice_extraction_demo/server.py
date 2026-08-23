"""FastAPI backend serving the Invoice Extraction demo UI."""
import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from invoice_extraction import extract_invoice, run_ocr

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_invoices")

SAMPLES = {
    "valid_supplies": {
        "file": "invoice_valid_supplies.png",
        "label": "Valid — hotel supplies",
    },
    "valid_fnb": {
        "file": "invoice_valid_fnb.png",
        "label": "Valid — F&B vendor",
    },
    "total_mismatch": {
        "file": "invoice_total_mismatch.png",
        "label": "Broken — total doesn't add up",
    },
    "missing_po": {
        "file": "invoice_missing_po.png",
        "label": "Broken — missing PO number",
    },
}

app = FastAPI(title="Elaf Group — Invoice Extraction Agent")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.get("/api/samples")
def list_samples():
    return [{"id": sid, "label": s["label"]} for sid, s in SAMPLES.items()]


@app.get("/api/sample-image/{sample_id}")
def sample_image(sample_id: str):
    if sample_id not in SAMPLES:
        raise HTTPException(404, "Unknown sample")
    return FileResponse(os.path.join(SAMPLE_DIR, SAMPLES[sample_id]["file"]))


def _process(image: Image.Image) -> dict:
    raw_text, conf = run_ocr(image)
    result = extract_invoice(raw_text, conf)
    checks = result["checks"]
    all_pass = all(
        checks.get(k, False)
        for k in ["subtotal_matches_line_items", "total_matches_subtotal_plus_tax", "has_po_number"]
    )
    return {
        "header": result["header"],
        "line_items": result["line_items"],
        "totals": result["totals"],
        "computed_subtotal": result["computed_subtotal"],
        "checks": checks,
        "decision": "approve" if all_pass else "review",
        "ocr_confidence": conf,
        "raw_text": raw_text,
    }


@app.post("/api/extract-sample/{sample_id}")
def extract_sample(sample_id: str):
    if sample_id not in SAMPLES:
        raise HTTPException(404, "Unknown sample")
    image = Image.open(os.path.join(SAMPLE_DIR, SAMPLES[sample_id]["file"])).convert("RGB")
    return _process(image)


@app.post("/api/extract-upload")
async def extract_upload(file: UploadFile = File(...)):
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(400, "Please upload a PNG or JPG image.")
    try:
        image = Image.open(file.file).convert("RGB")
    except Exception:
        raise HTTPException(400, "Could not read that image file.")
    return _process(image)
