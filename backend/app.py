# -*- coding: utf-8 -*-
"""
app.py  —  InvoiceIQ Backend
"""
import os
import uuid
import logging
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
import importlib.util
import sys

# Dynamically load the user's files with spaces
def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

base_dir = os.path.dirname(os.path.abspath(__file__))
ocr_module = load_module_from_path("ocr_cloud_final", os.path.join(base_dir, "OCR cloud final.py"))
baseline_module = load_module_from_path("baseline_ocr", os.path.join(base_dir, "baseline OCR.py"))

from database import init_db, save_record

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER    = os.path.join(base_dir, "uploads")
ALLOWED_EXTS     = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_SIZE_BYTES   = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()

def allowed(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTS

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    if not allowed(file.filename):
        return jsonify({"error": f"Unsupported file type. Allowed: PDF, JPG, PNG."}), 400

    file_bytes = file.read()
    if len(file_bytes) == 0:
        return jsonify({"error": "Uploaded file is empty."}), 400

    if len(file_bytes) > MAX_SIZE_BYTES:
        return jsonify({"error": "File exceeds the 10 MB size limit."}), 413

    ext       = os.path.splitext(file.filename)[1].lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, safe_name)

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    log.info("Saved upload: %s", safe_name)

    try:
        # Use the existing run_tesseract function
        raw_text = ocr_module.run_tesseract(save_path)
    except Exception as exc:
        log.error("OCR failed: %s", exc)
        return jsonify({"error": f"OCR processing failed: {exc}"}), 500

    try:
        # Use extract_original to avoid missing fallback parser error
        nested_fields = baseline_module.extract_original(raw_text)
        
        # Map nested structure to frontend flat structure
        fields = {
            "company_name": nested_fields.get("invoice", {}).get("seller_name") or nested_fields.get("invoice", {}).get("client_name") or "N/A",
            "date": nested_fields.get("invoice", {}).get("invoice_date") or "N/A",
            "total_amount": nested_fields.get("subtotal", {}).get("total") or "N/A",
            "invoice_number": nested_fields.get("invoice", {}).get("invoice_number") or "N/A",
            "tax_amount": nested_fields.get("subtotal", {}).get("tax") or "N/A",
            "vendor_address": nested_fields.get("invoice", {}).get("seller_address") or "N/A",
        }
    except Exception as exc:
        log.error("Extraction failed: %s", exc)
        return jsonify({"error": f"Field extraction failed: {exc}"}), 500

    try:
        save_record(
            filename   = file.filename,
            saved_as   = safe_name,
            raw_text   = raw_text,
            fields     = fields,
        )
    except Exception as exc:
        log.warning("DB save failed: %s", exc)

    return jsonify(fields), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()}), 200

@app.route("/records", methods=["GET"])
def records():
    from database import get_all_records
    try:
        rows = get_all_records()
        return jsonify(rows), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    print("\n  [OK] InvoiceIQ backend running at http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
