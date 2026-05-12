import re
from pathlib import Path



DATE_PATTERN = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
INVOICE_NO_PATTERN = re.compile(
    r"(?:invoice\s*(?:no|number|#)\s*[:\-]?\s*)([A-Z0-9\-]+)", re.IGNORECASE
)
TOTAL_PATTERN = re.compile(
    r"(?:total\s*[$:]?\s*)([\d\s]+[\.,]\d{2})", re.IGNORECASE
)
TAX_PATTERN = re.compile(
    r"(?:tax|vat)\s*[$:]?\s*([\d\s]+[\.,]\d{2})", re.IGNORECASE
)
DISCOUNT_PATTERN = re.compile(
    r"(?:discount)\s*[$:]?\s*([\d\s]+[\.,]\d{2})", re.IGNORECASE
)
IBAN_PATTERN = re.compile(r"\bIBAN\s*[:\-]?\s*([A-Z0-9]+)\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"\d[\d\s]*[\.,]\d{2}")
DUE_DATE_PATTERN = re.compile(
    r"(?:due\s*date\s*[:\-]?\s*)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE
)
SELLER_CLIENT_PATTERN = re.compile(
    r"Seller\s*:\s*(.*?)\s+Client\s*:\s*(.*?)\s+(?:\d|Tax\s*Id|IBAN|ITEMS)",
    re.IGNORECASE | re.DOTALL,
)

def normalize_space(value):
    return " ".join((value or "").replace("\n", " ").split())

def normalize_value(value):
    value = normalize_space(value)
    value = value.replace("$", "")
    value = re.sub(r"\s+", " ", value)
    money_like = re.fullmatch(r"[\d\s.,]+", value.strip())
    if money_like and ("," in value or "." in value):
        compact = value.replace(" ", "")
        last_dot = compact.rfind(".")
        last_comma = compact.rfind(",")
        if last_dot > last_comma:
            decimal_sep = "."
        else:
            decimal_sep = ","
        int_part, frac_part = compact.rsplit(decimal_sep, 1)
        int_part = int_part.replace(",", "").replace(".", "")
        value = f"{int_part}.{frac_part}"
    return value.strip().lower()

def normalize_space(value):
    return " ".join((value or "").replace("\n", " ").split())

def normalize_value(value):
    value = normalize_space(value)
    value = value.replace("$", "")
    value = re.sub(r"\s+", " ", value)
    money_like = re.fullmatch(r"[\d\s.,]+", value.strip())
    if money_like and ("," in value or "." in value):
        compact = value.replace(" ", "")
        last_dot = compact.rfind(".")
        last_comma = compact.rfind(",")
        if last_dot > last_comma:
            decimal_sep = "."
        else:
            decimal_sep = ","
        int_part, frac_part = compact.rsplit(decimal_sep, 1)
        int_part = int_part.replace(",", "").replace(".", "")
        value = f"{int_part}.{frac_part}"
    return value.strip().lower()

def build_default_output():
    return {
        "invoice": {
            "client_name": "", "client_address": "", "seller_name": "",
            "seller_address": "", "invoice_number": "", "invoice_date": "",
            "due_date": "",
        },
        "items": [],
        "item_count": "",
        "subtotal": {"tax": "", "discount": "", "total": ""},
        "payment_instructions": {
            "due_date": "", "bank_name": "", "account_number": "", "payment_method": "",
        },
    }

def extract_original(ocr_text):
    """Original extraction - works on training dataset"""
    result = build_default_output()
    text = normalize_space(ocr_text)
    invoice_no_match = INVOICE_NO_PATTERN.search(text)
    if invoice_no_match:
        result["invoice"]["invoice_number"] = invoice_no_match.group(1).strip()
    date_matches = DATE_PATTERN.findall(text)
    if date_matches:
        result["invoice"]["invoice_date"] = date_matches[0].strip()
    due_date_match = DUE_DATE_PATTERN.search(text)
    if due_date_match:
        result["invoice"]["due_date"] = due_date_match.group(1).strip()
        result["payment_instructions"]["due_date"] = due_date_match.group(1).strip()
    iban_match = IBAN_PATTERN.search(text)
    if iban_match:
        result["payment_instructions"]["account_number"] = iban_match.group(1).strip()
    seller_client_match = SELLER_CLIENT_PATTERN.search(text)
    if seller_client_match:
        result["invoice"]["seller_name"] = normalize_space(seller_client_match.group(1))
        result["invoice"]["client_name"] = normalize_space(seller_client_match.group(2))
    item_count = 0
    for line in text.splitlines():
        line = line.strip().lower()
        if "each" in line and re.search(r"\d[\d\s]*[\.,]\d{2}", line):
            item_count += 1
    if item_count:
        result["item_count"] = str(item_count)
    lower_text = text.lower()
    summary_start = lower_text.rfind("summary")
    summary_text = text[summary_start:] if summary_start != -1 else text
    summary_total_segments = list(re.finditer(r"Total.{0,180}", summary_text, flags=re.IGNORECASE))
    if summary_total_segments:
        amounts = AMOUNT_PATTERN.findall(summary_total_segments[-1].group(0))
        if amounts:
            result["subtotal"]["total"] = normalize_space(amounts[-1])
    if not result["subtotal"]["total"]:
        total_candidates = TOTAL_PATTERN.findall(text)
        if total_candidates:
            result["subtotal"]["total"] = normalize_space(total_candidates[-1])
    if not result["subtotal"]["total"]:
        total_segments = list(re.finditer(r"Total.{0,120}", text, flags=re.IGNORECASE))
        for match in reversed(total_segments):
            amounts = AMOUNT_PATTERN.findall(match.group(0))
            if amounts:
                result["subtotal"]["total"] = normalize_space(amounts[-1])
                break
    summary_vat_segments = list(re.finditer(r"(?:VAT|%|summary).{0,220}", summary_text, flags=re.IGNORECASE))
    for seg in reversed(summary_vat_segments):
        amounts = AMOUNT_PATTERN.findall(seg.group(0))
        if len(amounts) >= 3:
            result["subtotal"]["tax"] = normalize_space(amounts[-2])
            if not result["subtotal"]["total"]:
                result["subtotal"]["total"] = normalize_space(amounts[-1])
            break
    tax_candidates = TAX_PATTERN.findall(text)
    if tax_candidates:
        result["subtotal"]["tax"] = normalize_space(tax_candidates[-1])
    discount_candidates = DISCOUNT_PATTERN.findall(text)
    if discount_candidates:
        result["subtotal"]["discount"] = normalize_space(discount_candidates[-1])
    return result

def extract_with_regex(ocr_text):
    """Main extraction - tries original, then enhanced fallback"""
    from fallback_parser import simple_fallback_extract
    
    result = extract_original(ocr_text)
    has_total = result.get("subtotal", {}).get("total")
    has_invoice_no = result.get("invoice", {}).get("invoice_number")
    
    if not has_total and not has_invoice_no:
        fallback = simple_fallback_extract(ocr_text)
        if fallback["subtotal"]["total"]:
            result["subtotal"]["total"] = fallback["subtotal"]["total"]
        if fallback["invoice"]["invoice_number"]:
            result["invoice"]["invoice_number"] = fallback["invoice"]["invoice_number"]
        if fallback["invoice"]["invoice_date"]:
            result["invoice"]["invoice_date"] = fallback["invoice"]["invoice_date"]
        if fallback["invoice"]["client_name"]:
            result["invoice"]["client_name"] = fallback["invoice"]["client_name"]
        if fallback["invoice"]["seller_name"]:
            result["invoice"]["seller_name"] = fallback["invoice"]["seller_name"]
    
    return result

def get_value_by_field(obj, field):
    if field == "invoice.client_name":
        return str(obj.get("invoice", {}).get("client_name", "") or "")
    if field == "invoice.seller_name":
        return str(obj.get("invoice", {}).get("seller_name", "") or "")
    if field == "invoice.invoice_number":
        return str(obj.get("invoice", {}).get("invoice_number", "") or "")
    if field == "invoice.invoice_date":
        return str(obj.get("invoice", {}).get("invoice_date", "") or "")
    if field == "invoice.due_date":
        return str(obj.get("invoice", {}).get("due_date", "") or "")
    if field == "subtotal.total":
        return str(obj.get("subtotal", {}).get("total", "") or "")
    if field == "subtotal.tax":
        return str(obj.get("subtotal", {}).get("tax", "") or "")
    if field == "subtotal.discount":
        return str(obj.get("subtotal", {}).get("discount", "") or "")
    if field == "payment_instructions.account_number":
        return str(obj.get("payment_instructions", {}).get("account_number", "") or "")
    if field == "item_count":
        return str(obj.get("item_count", "") or "")
    return ""

def compute_f1(rows_truth_pred, fields):
    per_field = {}
    macro_f1_sum = 0.0
    for field in fields:
        tp = fp = fn = 0
        for row in rows_truth_pred:
            truth = normalize_value(get_value_by_field(row["truth"], field))
            pred = normalize_value(get_value_by_field(row["pred"], field))
            if pred == truth and truth:
                tp += 1
            elif pred and pred != truth:
                fp += 1
                if truth:
                    fn += 1
            elif not pred and truth:
                fn += 1
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_field[field] = {"precision": precision, "recall": recall, "f1": f1}
        macro_f1_sum += f1
    macro_f1 = macro_f1_sum / len(fields) if fields else 0.0
    return {"per_field": per_field, "macro_f1": macro_f1}

def evaluate_baseline(dataset_dir, labels_path, max_samples=None, verbose=False, cache_dir=None, refresh_cache=False):
    dataset_dir = Path(dataset_dir)
    labels_path = Path(labels_path)
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_dir}")
    if not labels_path.exists():
        raise FileNotFoundError(f"Labels not found at {labels_path}")
    
    
    rows = load_label_rows(labels_path=labels_path, max_samples=max_samples)
    rows_truth_pred = []
    cache_hits = 0
    cache_misses = 0
    for idx, row in enumerate(rows, start=1):
        image_path = dataset_dir / row["file_name"]
        if not image_path.exists():
            continue
        if cache_dir is not None:
            cache_path = cache_dir / _cache_key_for_image(image_path)
            had_cache = cache_path.exists() and not refresh_cache
            ocr_text = get_ocr_text_cached(image_path=image_path, cache_dir=cache_dir, refresh_cache=refresh_cache)
            if had_cache:
                cache_hits += 1
            else:
                cache_misses += 1
        else:
            ocr_text = run_tesseract(image_path)
        pred = extract_with_regex(ocr_text)
        rows_truth_pred.append({"truth": row["label"], "pred": pred, "file_name": row["file_name"]})
        if verbose and (idx % 20 == 0 or idx == len(rows)):
            print(f"Baseline progress: {idx}/{len(rows)}", flush=True)
    fields = ["invoice.client_name", "invoice.seller_name", "invoice.invoice_number",
              "invoice.invoice_date", "invoice.due_date", "subtotal.tax",
              "subtotal.discount", "subtotal.total", "payment_instructions.account_number", "item_count"]
    key_fields = ["invoice.client_name", "invoice.invoice_number", "invoice.invoice_date", "subtotal.total"]
    metrics = compute_f1(rows_truth_pred, fields)
    key_metrics = compute_f1(rows_truth_pred, key_fields)
    return {
        "samples_used": len(rows_truth_pred),
        "ocr_source": "tesseract",
        "cache_dir": str(cache_dir) if cache_dir else None,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "fields": fields,
        "metrics": metrics,
        "key_fields": key_fields,
        "key_metrics": key_metrics,
    }
