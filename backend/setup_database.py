"""
setup_database.py — Rebuild inventory.db from CSV seed files.

Usage:
    cd backend
    python setup_database.py

This script:
 1. Creates all SQLAlchemy tables (products, sales_history, forecasts, etc.)
 2. Loads data/products_50k.csv  → products table   (50,000 rows)
 3. Loads data/sales_dense.csv   → sales_history     (2M rows)

Runtime: ~30-60 seconds depending on hardware.
"""
import os
import sys
import time
import sqlite3

import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "inventory.db")
DATA_DIR   = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

PRODUCTS_CSV = os.path.join(DATA_DIR, "products_50k.csv")
SALES_CSV    = os.path.join(DATA_DIR, "sales_dense.csv")


def main():
    t0 = time.time()

    # ── Pre-checks ─────────────────────────────────────────────────────────────
    if os.path.exists(DB_PATH):
        size_mb = os.path.getsize(DB_PATH) / 1024 / 1024
        print(f"⚠  inventory.db already exists ({size_mb:.1f} MB).")
        ans = input("   Overwrite? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted.")
            sys.exit(0)
        os.remove(DB_PATH)
        # Remove WAL/SHM leftover files too
        for ext in ["-wal", "-shm", "-journal"]:
            p = DB_PATH + ext
            if os.path.exists(p):
                os.remove(p)

    for path, label in [(PRODUCTS_CSV, "products_50k.csv"), (SALES_CSV, "sales_dense.csv")]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found at {path}")
            sys.exit(1)

    # ── 1. Create tables via SQLAlchemy ────────────────────────────────────────
    print("\n[1/3] Creating database tables …")
    # Import the app modules so SQLAlchemy creates proper INTEGER PRIMARY KEY
    sys.path.insert(0, SCRIPT_DIR)
    from app.database import engine, Base
    from app.database.models import Product, SalesHistory  # noqa: F401 — ensures models are registered

    Base.metadata.create_all(bind=engine)
    print("      Tables created ✓")

    # ── 2. Load products ───────────────────────────────────────────────────────
    print(f"\n[2/3] Loading products from {os.path.basename(PRODUCTS_CSV)} …")
    products_df = pd.read_csv(PRODUCTS_CSV)
    print(f"      Read {len(products_df):,} rows, {len(products_df.columns)} columns")

    # Map CSV columns → DB columns
    # CSV has: sku, name, category, unit_price, unit_cost, current_stock, lead_time_days, ...
    # All column names already match the Product model (the CSV was generated from it)
    # We need to add an 'id' column (1-based sequential) since the table uses INTEGER PRIMARY KEY
    products_df.insert(0, "id", range(1, len(products_df) + 1))

    # Write to DB using optimized chunked insert
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA temp_store=MEMORY")

    products_df.to_sql("products", conn, if_exists="append", index=False, chunksize=5000)
    products_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"      Loaded {products_count:,} products ✓")

    # ── 3. Load sales ─────────────────────────────────────────────────────────
    print(f"\n[3/3] Loading sales from {os.path.basename(SALES_CSV)} …")
    sales_df = pd.read_csv(SALES_CSV)
    print(f"      Read {len(sales_df):,} rows")

    # Add id column
    sales_df.insert(0, "id", range(1, len(sales_df) + 1))

    sales_df.to_sql("sales_history", conn, if_exists="append", index=False, chunksize=10000)
    sales_count = conn.execute("SELECT COUNT(*) FROM sales_history").fetchone()[0]
    print(f"      Loaded {sales_count:,} sales records ✓")

    # ── Create indexes (pandas to_sql doesn't create them) ─────────────────────
    print("\n      Creating indexes …")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_products_id ON products (id)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_products_sku ON products (sku)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_products_name ON products (name)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_products_category ON products (category)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_sales_history_id ON sales_history (id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_sales_history_date ON sales_history (date)")
    conn.commit()

    # ── Verify schema ──────────────────────────────────────────────────────────
    for table in ["products", "sales_history"]:
        sql = conn.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'"
        ).fetchone()[0]
        if "INTEGER NOT NULL" in sql:
            print(f"      {table}: INTEGER PRIMARY KEY ✓")
        else:
            print(f"      {table}: WARNING — check schema")

    conn.execute("PRAGMA optimize")
    conn.close()

    elapsed = time.time() - t0
    db_size = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f"\n✅  Database ready: {DB_PATH}")
    print(f"    Size: {db_size:.1f} MB  |  Time: {elapsed:.1f}s")
    print(f"    Products: {products_count:,}  |  Sales: {sales_count:,}")


if __name__ == "__main__":
    main()
