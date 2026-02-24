"""
Two-Tier JSON Storage Utility
=============================
Tier 1: Save raw JSON responses to local file system (audit trail + replay)
Tier 2: Process and persist into SQLite via existing DataMapper pipeline

Directory structure:
    backend/data/api_imports/
    ├── raw/               # Untouched API responses
    │   ├── products_fakestoreapi_2026-02-20_143000.json
    │   ├── products_dummyjson_2026-02-20_150000.json
    │   └── ...
    ├── processed/         # Post-mapping snapshots (optional)
    │   └── products_fakestoreapi_2026-02-20_143000_mapped.json
    └── manifest.json      # Master index of all imports
"""

import json
import os
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse


# Resolve base directory: backend/data/api_imports/
_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "api_imports"
)
RAW_DIR = os.path.join(_BASE_DIR, "raw")
PROCESSED_DIR = os.path.join(_BASE_DIR, "processed")
MANIFEST_PATH = os.path.join(_BASE_DIR, "manifest.json")

# Ensure directories exist at import time
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


# ── Source-name extraction ──────────────────────────────────────────

# Map known domains to clean source names
_KNOWN_SOURCES = {
    "fakestoreapi.com": "fakestoreapi",
    "dummyjson.com": "dummyjson",
    "openlibrary.org": "openlibrary",
    "api.coingecko.com": "coingecko",
    "restcountries.com": "restcountries",
    "pokeapi.co": "pokeapi",
}


def _derive_source_name(url: str) -> str:
    """Extract a clean, human-readable source name from a URL."""
    try:
        host = urlparse(url).hostname or ""
        # Check known sources first
        for domain, name in _KNOWN_SOURCES.items():
            if domain in host:
                return name
        # Fallback: use second-level domain  (e.g. "example" from "api.example.com")
        parts = host.replace("www.", "").split(".")
        return parts[-2] if len(parts) >= 2 else parts[0]
    except Exception:
        return "unknown_api"


# ── File naming ─────────────────────────────────────────────────────

def _build_filename(data_type: str, source_name: str, suffix: str = "") -> str:
    """
    Build a clean, descriptive filename.
    
    Examples:
        products_fakestoreapi_2026-02-20_143000.json
        products_dummyjson_2026-02-20_150000_mapped.json
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    parts = [data_type, source_name, ts]
    if suffix:
        parts.append(suffix)
    return "_".join(parts) + ".json"


# ── Tier 1: Save raw JSON to disk ──────────────────────────────────

def save_raw_json(
    data: any,
    url: str,
    data_type: str = "products",
    source_name: Optional[str] = None
) -> dict:
    """
    Tier 1 — persist the raw API response to local disk.
    
    Returns:
        dict with keys: file_path, file_name, file_size_bytes, source_name
    """
    if source_name is None:
        source_name = _derive_source_name(url)

    file_name = _build_filename(data_type, source_name)
    file_path = os.path.join(RAW_DIR, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    file_size = os.path.getsize(file_path)

    return {
        "file_path": file_path,
        "file_name": file_name,
        "file_size_bytes": file_size,
        "source_name": source_name,
    }


# ── Save processed / mapped data (optional Tier 1b) ────────────────

def save_processed_json(
    mapped_records: list,
    url: str,
    data_type: str = "products",
    source_name: Optional[str] = None
) -> str:
    """Save the post-mapping snapshot so we can see exactly what went into the DB."""
    if source_name is None:
        source_name = _derive_source_name(url)

    file_name = _build_filename(data_type, source_name, suffix="mapped")
    file_path = os.path.join(PROCESSED_DIR, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(mapped_records, f, indent=2, default=str)

    return file_path


# ── Manifest management ────────────────────────────────────────────

def _load_manifest() -> list:
    """Load the manifest index or return empty list."""
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_manifest(entries: list):
    """Persist manifest index to disk."""
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, default=str)


def append_to_manifest(entry: dict):
    """Add an import record to the manifest index."""
    entries = _load_manifest()
    entries.append(entry)
    _save_manifest(entries)


def get_manifest() -> list:
    """Return the full manifest index."""
    return _load_manifest()


# ── List saved raw files ────────────────────────────────────────────

def list_raw_files() -> list:
    """Return metadata for all saved raw JSON files."""
    files = []
    for fname in sorted(os.listdir(RAW_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(RAW_DIR, fname)
        files.append({
            "file_name": fname,
            "file_path": fpath,
            "file_size_bytes": os.path.getsize(fpath),
            "modified_at": datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat(),
        })
    return files


# ── Load a raw file for replay ──────────────────────────────────────

def load_raw_json(file_name: str) -> dict:
    """Load and parse a previously saved raw JSON file."""
    file_path = os.path.join(RAW_DIR, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Raw file not found: {file_name}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
