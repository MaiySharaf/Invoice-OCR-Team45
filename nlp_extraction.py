import random
import re
from pathlib import Path

import spacy
from spacy.training import Example

from ocr_engine import (
    build_default_output,
    compute_f1,
    extract_with_regex,
    get_ocr_text_cached,
    load_label_rows,
    normalize_space,
    run_tesseract,
)

FIELD_TO_LABEL = {
    "invoice.client_name": "CLIENT_NAME",
    "invoice.seller_name": "SELLER_NAME",
    "invoice.invoice_number": "INVOICE_NUMBER",
    "invoice.invoice_date": "INVOICE_DATE",
    "invoice.due_date": "DUE_DATE",
    "subtotal.tax": "TAX_AMOUNT",
    "subtotal.discount": "DISCOUNT_AMOUNT",
    "subtotal.total": "TOTAL_AMOUNT",
    "payment_instructions.account_number": "ACCOUNT_NUMBER",
}
LABEL_TO_FIELD = {v: k for k, v in FIELD_TO_LABEL.items()}
AMOUNT_PATTERN = re.compile(r"\d[\d\s]*[\.,]\d{2}")


def get_label_value(obj, field):
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
    if field == "subtotal.tax":
        return str(obj.get("subtotal", {}).get("tax", "") or "")
    if field == "subtotal.discount":
        return str(obj.get("subtotal", {}).get("discount", "") or "")
    if field == "subtotal.total":
        return str(obj.get("subtotal", {}).get("total", "") or "")
    if field == "payment_instructions.account_number":
        return str(obj.get("payment_instructions", {}).get("account_number", "") or "")
    if field == "item_count":
        return str(obj.get("item_count", "") or "")
    return ""


def set_pred_value(obj, field, value):
    if field == "invoice.client_name":
        obj["invoice"]["client_name"] = value
    elif field == "invoice.seller_name":
        obj["invoice"]["seller_name"] = value
    elif field == "invoice.invoice_number":
        obj["invoice"]["invoice_number"] = value
    elif field == "invoice.invoice_date":
        obj["invoice"]["invoice_date"] = value
    elif field == "invoice.due_date":
        obj["invoice"]["due_date"] = value
    elif field == "subtotal.tax":
        obj["subtotal"]["tax"] = value
    elif field == "subtotal.discount":
        obj["subtotal"]["discount"] = value
    elif field == "subtotal.total":
        obj["subtotal"]["total"] = value
    elif field == "payment_instructions.account_number":
        obj["payment_instructions"]["account_number"] = value
    elif field == "item_count":
        obj["item_count"] = value


def find_span_case_insensitive(text, value):
    if not value:
        return None
    clean_val = normalize_space(value)
    if not clean_val:
        return None

    low_text = text.lower()
    low_val = clean_val.lower()
    idx = low_text.find(low_val)
    if idx == -1:
        return None
    return (idx, idx + len(clean_val))


def extract_total_fallback(text):
    compact = normalize_space(text)
    low = compact.lower()

    start = low.rfind("summary")
    if start == -1:
        return ""
    segment = compact[start:]

    total_positions = [m.start() for m in re.finditer(r"\btotal\b", segment, flags=re.IGNORECASE)]
    if total_positions:
        idx = total_positions[-1]
        around = segment[idx : idx + 120]
        amounts = AMOUNT_PATTERN.findall(around)
        if len(amounts) >= 2:
            return normalize_space(amounts[-1])

    tail_amounts = AMOUNT_PATTERN.findall(segment[-220:])
    if len(tail_amounts) >= 2:
        return normalize_space(tail_amounts[-1])

    return ""


def build_spacy_examples(rows):
    examples = []

    for row in rows:
        text = normalize_space(row["ocr_text"])
        entities = []

        for field_path, label in FIELD_TO_LABEL.items():
            gold = get_label_value(row["label"], field_path)
            span = find_span_case_insensitive(text, gold)
            if span:
                entities.append((span[0], span[1], label))

        if entities:
            examples.append((text, {"entities": entities}))

    return examples


def train_nlp_model(
    train_rows,
    model_output_dir,
    n_iter=15,
    verbose=False,
):
    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")

    for label in FIELD_TO_LABEL.values():
        ner.add_label(label)

    train_data = build_spacy_examples(train_rows)
    if not train_data:
        raise RuntimeError("No train entities found. Check labels or OCR source.")

    optimizer = nlp.begin_training()

    for epoch in range(1, n_iter + 1):
        random.shuffle(train_data)
        losses = {}

        for text, ann in train_data:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, ann)
            nlp.update([example], sgd=optimizer, losses=losses, drop=0.2)

        if verbose and (epoch == 1 or epoch == n_iter or epoch % 5 == 0):
            print(f"NLP training epoch {epoch}/{n_iter}", flush=True)

    model_output_dir.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(model_output_dir)
    return model_output_dir


def predict_with_trained_nlp(nlp, ocr_text):
    """ORIGINAL WORKING VERSION - DO NOT MODIFY"""
    result = build_default_output()
    doc = nlp(normalize_space(ocr_text))

    for ent in doc.ents:
        field = LABEL_TO_FIELD.get(ent.label_)
        if not field:
            continue

        current_val = get_label_value(result, field)
        candidate = ent.text.strip()

        if not current_val or len(candidate) > len(current_val):
            set_pred_value(result, field, candidate)
    
    if not get_label_value(result, "subtotal.total"):
        set_pred_value(result, "subtotal.total", extract_total_fallback(ocr_text))

    # CRITICAL: This fallback to regex is what makes it work!
    regex_result = extract_with_regex(ocr_text)
    for field in FIELD_TO_LABEL.keys():
        if not get_label_value(result, field):
            set_pred_value(result, field, get_label_value(regex_result, field))

    return result


def evaluate_nlp_pipeline(
    dataset_dir,
    labels_path,
    max_samples=300,
    test_ratio=0.2,
    n_iter=15,
    verbose=False,
    cache_dir=None,
    refresh_cache=False,
):
    raw_rows = load_label_rows(labels_path=labels_path, max_samples=max_samples)

    rows = []
    cache_hits = 0
    cache_misses = 0

    for idx, row in enumerate(raw_rows, start=1):
        image_path = dataset_dir / row["file_name"]
        if not image_path.exists():
            continue

        if cache_dir is not None:
            cache_path = cache_dir / f"{image_path.stem}.json"
            had_cache = cache_path.exists() and not refresh_cache
            ocr_text = get_ocr_text_cached(image_path=image_path, cache_dir=cache_dir, refresh_cache=refresh_cache)
            if had_cache:
                cache_hits += 1
            else:
                cache_misses += 1
        else:
            ocr_text = run_tesseract(image_path)

        rows.append(
            {
                "file_name": row["file_name"],
                "label": row["label"],
                "ocr_text": ocr_text,
            }
        )

        if verbose and (idx % 20 == 0 or idx == len(raw_rows)):
            print(f"NLP data prep progress: {idx}/{len(raw_rows)}", flush=True)

    if len(rows) < 20:
        raise RuntimeError("Need at least 20 samples to run train/test evaluation.")

    random.seed(42)
    random.shuffle(rows)

    split_idx = int(len(rows) * (1 - test_ratio))
    train_rows = rows[:split_idx]
    test_rows = rows[split_idx:]

    model_dir = Path("artifacts") / "spacy_ocr_ner"
    if verbose:
        print(f"Training NLP model on {len(train_rows)} samples", flush=True)
    train_nlp_model(train_rows=train_rows, model_output_dir=model_dir, n_iter=n_iter, verbose=verbose)

    nlp = spacy.load(model_dir)

    fields = [
        "invoice.client_name",
        "invoice.seller_name",
        "invoice.invoice_number",
        "invoice.invoice_date",
        "invoice.due_date",
        "subtotal.tax",
        "subtotal.discount",
        "subtotal.total",
        "payment_instructions.account_number",
        "item_count",
    ]
    key_fields = [
        "invoice.client_name",
        "invoice.invoice_number",
        "invoice.invoice_date",
        "subtotal.total",
    ]
    baseline_pairs = []
    nlp_pairs = []

    for row in test_rows:
        pred_baseline = extract_with_regex(row["ocr_text"])
        pred_nlp = predict_with_trained_nlp(nlp, row["ocr_text"])
        nlp_pairs.append({"truth": row["label"], "pred": pred_nlp, "file_name": row["file_name"]})
        baseline_pairs.append({"truth": row["label"], "pred": pred_baseline, "file_name": row["file_name"]})

    if verbose:
        print(f"Evaluated on {len(test_rows)} test samples", flush=True)

    baseline_metrics = compute_f1(baseline_pairs, fields)
    nlp_metrics = compute_f1(nlp_pairs, fields)
    baseline_key_metrics = compute_f1(baseline_pairs, key_fields)
    nlp_key_metrics = compute_f1(nlp_pairs, key_fields)

    return {
        "samples_total": len(rows),
        "samples_train": len(train_rows),
        "samples_test": len(test_rows),
        "ocr_source": "tesseract",
        "cache_dir": str(cache_dir) if cache_dir else None,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "fields": fields,
        "baseline_metrics_reference": baseline_metrics,
        "nlp_metrics": nlp_metrics,
        "key_fields": key_fields,
        "baseline_key_metrics": baseline_key_metrics,
        "baseline_key_metrics_reference": baseline_key_metrics,
        "nlp_key_metrics": nlp_key_metrics,
    }