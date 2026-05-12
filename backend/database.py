# -*- coding: utf-8 -*-
"""
database.py  —  SQLite Persistence Layer
InvoiceIQ Backend — Cloud Computing Spring 2026

Creates and manages a local SQLite database to store:
  - Every uploaded document (filename, path)
  - Extracted fields (company, date, total, etc.)
  - Raw OCR text
  - Timestamp

Tables:
  extractions — one row per uploaded document
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Dict, List

DB_PATH = os.path.join(os.path.dirname(__file__), "invoiceiq.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS extractions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    original_name   TEXT    NOT NULL,
    saved_as        TEXT    NOT NULL,
    company_name    TEXT,
    date            TEXT,
    total_amount    TEXT,
    invoice_number  TEXT,
    tax_amount      TEXT,
    vendor_address  TEXT,
    raw_text        TEXT,
    extra_fields    TEXT,           -- JSON blob for any additional fields
    created_at      TEXT    NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # dict-like rows
    return conn


def init_db() -> None:
    """Create database tables if they don't already exist."""
    with _connect() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


def save_record(
    filename:  str,
    saved_as:  str,
    raw_text:  str,
    fields:    Dict[str, str],
) -> int:
    """
    Insert an extraction record into SQLite.

    Args:
        filename:  Original filename from the user.
        saved_as:  UUID-based filename saved to disk.
        raw_text:  Full OCR text.
        fields:    Dict returned by nlp_extractor.extract_fields().

    Returns:
        The new row ID.
    """
    known_keys = {"company_name", "date", "total_amount",
                  "invoice_number", "tax_amount", "vendor_address"}

    extra = {k: v for k, v in fields.items() if k not in known_keys}

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO extractions
                (original_name, saved_as,
                 company_name, date, total_amount,
                 invoice_number, tax_amount, vendor_address,
                 raw_text, extra_fields, created_at)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                saved_as,
                fields.get("company_name", "N/A"),
                fields.get("date",         "N/A"),
                fields.get("total_amount", "N/A"),
                fields.get("invoice_number", "N/A"),
                fields.get("tax_amount",   "N/A"),
                fields.get("vendor_address", "N/A"),
                raw_text,
                json.dumps(extra) if extra else None,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_records() -> List[Dict]:
    """Return all extraction records, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM extractions ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]
