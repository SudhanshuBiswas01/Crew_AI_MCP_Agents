"""
fetch_data.py — Download and clean the Olist public e-commerce dataset
=======================================================================
Uses the Kaggle API to download the official Olist dataset, merges the
orders + items tables, cleans and renames columns, samples 40 rows with a
balanced status mix, and saves to data/inventory_orders.csv.

PRE-REQUISITES
--------------
1. Install kaggle:   pip install kaggle
2. Create an API token at https://www.kaggle.com/settings → "Create New Token"
   This downloads kaggle.json.
3. Place kaggle.json at one of these locations:
   - Windows: C:/Users/<you>/.kaggle/kaggle.json
   - Linux/macOS: ~/.kaggle/kaggle.json
   OR set the environment variables KAGGLE_USERNAME and KAGGLE_KEY in your .env

4. Run:  uv run python fetch_data.py

WHAT IT DOES
------------
Downloads:
  olist_orders_dataset.csv        (99k rows — orders)
  olist_order_items_dataset.csv   (112k rows — items per order)

Merges on order_id, renames columns, samples 40 balanced rows, saves to:
  data/inventory_orders.csv

Dataset citation:
  Olist. (2018). Brazilian E-Commerce Public Dataset by Olist.
  Kaggle. https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
  License: CC BY-NC-SA 4.0
"""

import os
import pathlib
import shutil
import sys
import zipfile
from io import StringIO

import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────

KAGGLE_DATASET  = "olistbr/brazilian-ecommerce"
ORDERS_FILE     = "olist_orders_dataset.csv"
ITEMS_FILE      = "olist_order_items_dataset.csv"
OUTPUT_PATH     = pathlib.Path(__file__).parent / "data" / "inventory_orders.csv"
DOWNLOAD_DIR    = pathlib.Path(__file__).parent / "data" / "_kaggle_tmp"
SAMPLE_SIZE     = 40
TARGET_STATUSES = ["delivered", "shipped", "canceled", "invoiced", "processing"]

# ── Load .env so KAGGLE_USERNAME / KAGGLE_KEY are available ──────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def check_kaggle_credentials() -> None:
    """Abort with a clear message if Kaggle credentials are missing."""
    has_env = os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY")
    has_json = (
        pathlib.Path.home() / ".kaggle" / "kaggle.json"
    ).exists()
    if not has_env and not has_json:
        print(
            "\nERROR: Kaggle credentials not found.\n"
            "\nTo fix this:\n"
            "  1. Go to https://www.kaggle.com/settings → 'Create New Token'\n"
            "  2. Save the downloaded kaggle.json to:\n"
            "       Windows:  C:\\Users\\<you>\\.kaggle\\kaggle.json\n"
            "       Linux/Mac: ~/.kaggle/kaggle.json\n"
            "  OR add these lines to your .env file:\n"
            "       KAGGLE_USERNAME=your_username\n"
            "       KAGGLE_KEY=your_api_key\n"
            "\nThen re-run:  uv run python fetch_data.py\n"
        )
        sys.exit(1)


def download_olist(download_dir: pathlib.Path) -> dict[str, pathlib.Path]:
    """Download the Olist dataset zip via the Kaggle API and extract it."""
    try:
        import kaggle  # noqa: F401
    except ImportError:
        print("ERROR: kaggle package not installed. Run:  pip install kaggle")
        sys.exit(1)

    from kaggle.api.kaggle_api_extended import KaggleApiExtended
    api = KaggleApiExtended()
    api.authenticate()

    download_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading dataset '{KAGGLE_DATASET}' via Kaggle API...")
    api.dataset_download_files(KAGGLE_DATASET, path=str(download_dir), unzip=True, quiet=False)
    print("  Download complete.")

    found = {f.name: f for f in download_dir.rglob("*.csv")}
    missing = [n for n in [ORDERS_FILE, ITEMS_FILE] if n not in found]
    if missing:
        print(f"ERROR: Expected files not found in download: {missing}")
        print(f"  Files available: {list(found.keys())}")
        sys.exit(1)

    return {ORDERS_FILE: found[ORDERS_FILE], ITEMS_FILE: found[ITEMS_FILE]}


def balanced_sample(df: pd.DataFrame, total: int, statuses: list[str]) -> pd.DataFrame:
    """
    Sample rows with a balanced spread across order statuses.
    Fills remaining slots with 'delivered' rows if needed.
    """
    per_status = total // len(statuses)
    remainder  = total % len(statuses)
    frames = []

    for i, status in enumerate(statuses):
        subset = df[df["status"] == status]
        n = per_status + (1 if i < remainder else 0)
        if len(subset) == 0:
            print(f"  WARN: No rows with status='{status}', skipping.")
            continue
        sampled = subset.sample(n=min(n, len(subset)), random_state=42)
        frames.append(sampled)
        print(f"  Sampled {len(sampled):>2} rows with status='{status}'")

    result = pd.concat(frames, ignore_index=True)

    # Top-up with delivered rows if short
    if len(result) < total:
        shortfall = total - len(result)
        already_ids = set(result["order_id"].tolist())
        extra = (
            df[(df["status"] == "delivered") & (~df["order_id"].isin(already_ids))]
            .sample(n=min(shortfall, len(df)), random_state=99)
        )
        result = pd.concat([result, extra], ignore_index=True)
        print(f"  Topped up with {len(extra)} extra 'delivered' rows")

    return result.sample(frac=1, random_state=7).reset_index(drop=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n=== Olist Dataset Fetch & Clean ===\n")

    # 0. Check credentials
    check_kaggle_credentials()

    # 1. Download
    print("[1/5] Downloading from Kaggle...")
    files = download_olist(DOWNLOAD_DIR)

    # 2. Load CSVs
    print("\n[2/5] Loading CSVs...")
    orders = pd.read_csv(files[ORDERS_FILE])
    items  = pd.read_csv(files[ITEMS_FILE])
    print(f"  orders: {len(orders):,} rows")
    print(f"  items:  {len(items):,} rows")

    # 3. Merge on order_id (keep one item per order — cheapest item)
    print("\n[3/5] Merging on order_id...")
    items_min = items.sort_values("price").drop_duplicates(subset="order_id", keep="first")
    merged = pd.merge(orders, items_min[["order_id", "price"]], on="order_id", how="inner")
    print(f"  Merged: {len(merged):,} unique orders with price data")

    # 4. Select, rename, clean columns
    print("\n[4/5] Selecting and renaming columns...")
    df = merged[[
        "order_id",
        "order_status",
        "price",
        "order_purchase_timestamp",
        "customer_id",          # anonymised UUID — no PII
    ]].copy()

    df.rename(columns={
        "order_status":             "status",
        "price":                    "unit_price",
        "order_purchase_timestamp": "order_date",
        "customer_id":              "customer_region",  # proxy for region
    }, inplace=True)

    # Use first 8 chars of customer_id as an anonymous region tag
    df["customer_region"] = df["customer_region"].str[:8].str.upper()

    # Truncate order_id to 12 chars for readability
    df["order_id"] = df["order_id"].str[:12].str.upper()

    # Clean dates and status
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["status"]     = df["status"].str.strip().str.lower()

    # Add a sequential integer id for read_record() lookups
    df.insert(0, "id", range(1, len(df) + 1))

    print(f"  Columns: {list(df.columns)}")
    print(f"  Status distribution:\n{df['status'].value_counts().to_string()}")

    # 5. Sample 40 balanced rows
    print(f"\n[5/5] Sampling {SAMPLE_SIZE} rows (balanced by status)...")
    sample = balanced_sample(df, SAMPLE_SIZE, TARGET_STATUSES)
    sample = sample.reset_index(drop=True)
    sample["id"] = sample.index + 1

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(sample)} rows → {OUTPUT_PATH}")

    # Preview
    print("\nPreview (first 5 rows):")
    print(sample.head().to_string(index=False))

    # Cleanup temp download
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
    print(f"\nCleaned up temp dir: {DOWNLOAD_DIR}")
    print("\nDone.")


if __name__ == "__main__":
    main()
