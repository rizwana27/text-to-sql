#!/usr/bin/env python3
"""
data/seed.py — Download and load the Olist Brazilian E-Commerce dataset into the star schema.

Usage:
    # Download CSVs manually from Kaggle:
    # https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
    # Place all CSV files in ./data/raw/ then run:
    python -m data.seed

    # Or with auto-download via Kaggle API (requires ~/.kaggle/kaggle.json):
    KAGGLE_AUTO_DOWNLOAD=1 python -m data.seed
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import inspect

from model.database import get_engine
from model.schema import (
    Base,
    DimGeography,
    DimProducts,
    DimReviews,
    DimSellers,
    DimUsers,
    FactOrders,
)

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent / "raw"

CSV_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
}

# Approximate USD/BRL exchange rate for conversion
BRL_TO_USD = 0.20


def maybe_download_from_kaggle() -> None:
    """Attempt to download dataset via Kaggle API if KAGGLE_AUTO_DOWNLOAD is set."""
    if not os.getenv("KAGGLE_AUTO_DOWNLOAD"):
        return
    try:
        import kaggle  # type: ignore

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading Olist dataset from Kaggle...")
        kaggle.api.dataset_download_files(
            "olistbr/brazilian-ecommerce",
            path=str(RAW_DIR),
            unzip=True,
        )
        logger.info("Kaggle download complete.")
    except Exception as exc:
        logger.error("Kaggle download failed: %s", exc)
        logger.error(
            "Please manually download the Olist dataset from:\n"
            "  https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce\n"
            "and place the CSV files in ./data/raw/"
        )
        sys.exit(1)


def check_csv_files() -> bool:
    """Return True if all required CSV files are present."""
    missing = [name for name in CSV_FILES.values() if not (RAW_DIR / name).exists()]
    if missing:
        logger.error(
            "Missing CSV files in %s:\n  %s\n\n"
            "Download the Olist dataset from Kaggle:\n"
            "  https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce\n"
            "or set KAGGLE_AUTO_DOWNLOAD=1 to auto-download.",
            RAW_DIR,
            "\n  ".join(missing),
        )
        return False
    return True


def load_dim_users(customers_df: pd.DataFrame, engine) -> None:
    """Load dim_users from olist_customers_dataset.csv."""
    logger.info("Loading dim_users (%d rows)...", len(customers_df))
    records = []
    for _, row in customers_df.iterrows():
        records.append(
            {
                "user_id": str(row["customer_unique_id"]),
                "city": str(row.get("customer_city", "")).strip().title() or None,
                "state": str(row.get("customer_state", "")).strip().upper() or None,
                "signup_country_code": "BR",
                "is_active_member": True,
            }
        )
    # Deduplicate by user_id
    seen: set[str] = set()
    unique_records = []
    for r in records:
        if r["user_id"] not in seen:
            seen.add(r["user_id"])
            unique_records.append(r)

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        for chunk_start in range(0, len(unique_records), 1000):
            chunk = unique_records[chunk_start : chunk_start + 1000]
            session.bulk_insert_mappings(DimUsers, chunk)
            session.commit()
    logger.info("dim_users loaded: %d unique customers.", len(unique_records))


def load_dim_products(products_df: pd.DataFrame, engine) -> None:
    """Load dim_products from olist_products_dataset.csv."""
    logger.info("Loading dim_products (%d rows)...", len(products_df))
    records = []
    for _, row in products_df.iterrows():
        category_raw = row.get("product_category_name_english") or row.get("product_category_name") or ""
        records.append(
            {
                "product_id": str(row["product_id"]),
                "category_name": str(category_raw).strip().replace("_", " ").title() or None,
                "photos_qty": int(row["product_photos_qty"]) if pd.notna(row.get("product_photos_qty")) else 0,
            }
        )

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        for chunk_start in range(0, len(records), 1000):
            chunk = records[chunk_start : chunk_start + 1000]
            session.bulk_insert_mappings(DimProducts, chunk)
            session.commit()
    logger.info("dim_products loaded: %d products.", len(records))


def load_dim_sellers(sellers_df: pd.DataFrame, engine) -> None:
    """Load dim_sellers from olist_sellers_dataset.csv."""
    logger.info("Loading dim_sellers (%d rows)...", len(sellers_df))
    records = [
        {
            "seller_id": str(row["seller_id"]),
            "seller_city": str(row.get("seller_city", "")).strip().title() or None,
            "seller_state": str(row.get("seller_state", "")).strip().upper() or None,
        }
        for _, row in sellers_df.iterrows()
    ]

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        for chunk_start in range(0, len(records), 1000):
            chunk = records[chunk_start : chunk_start + 1000]
            session.bulk_insert_mappings(DimSellers, chunk)
            session.commit()
    logger.info("dim_sellers loaded: %d sellers.", len(records))


def load_dim_geography(geo_df: pd.DataFrame, engine) -> None:
    """Load dim_geography from olist_geolocation_dataset.csv (deduplicated by zip+city)."""
    logger.info("Loading dim_geography (raw %d rows)...", len(geo_df))
    geo_dedup = geo_df.drop_duplicates(subset=["geolocation_zip_code_prefix", "geolocation_city"])
    records = [
        {
            "zip_code_prefix": str(row["geolocation_zip_code_prefix"]).zfill(5),
            "city": str(row.get("geolocation_city", "")).strip().title() or None,
            "state": str(row.get("geolocation_state", "")).strip().upper() or None,
            "lat": float(row["geolocation_lat"]) if pd.notna(row.get("geolocation_lat")) else None,
            "lng": float(row["geolocation_lng"]) if pd.notna(row.get("geolocation_lng")) else None,
        }
        for _, row in geo_dedup.iterrows()
    ]

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        for chunk_start in range(0, len(records), 2000):
            chunk = records[chunk_start : chunk_start + 2000]
            session.bulk_insert_mappings(DimGeography, chunk)
            session.commit()
    logger.info("dim_geography loaded: %d unique zip+city combinations.", len(records))


def load_fact_orders(
    orders_df: pd.DataFrame,
    items_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    engine,
) -> None:
    """
    Load fact_orders by joining orders → order_items → customers.
    Each order_item becomes one fact row. Revenue is converted BRL → USD.
    """
    logger.info("Joining orders + order_items for fact_orders...")
    # Map customer_id → customer_unique_id
    cust_map = customers_df.set_index("customer_id")["customer_unique_id"].to_dict()

    merged = pd.merge(orders_df, items_df, on="order_id", how="left")
    logger.info("Merged orders+items: %d rows", len(merged))

    records = []
    for _, row in merged.iterrows():
        price = float(row["price"]) if pd.notna(row.get("price")) else 0.0
        freight = float(row["freight_value"]) if pd.notna(row.get("freight_value")) else 0.0
        cust_id = str(row.get("customer_id", ""))
        unique_id = cust_map.get(cust_id, cust_id)
        order_date_raw = row.get("order_purchase_timestamp")
        if pd.notna(order_date_raw):
            try:
                order_date = pd.to_datetime(order_date_raw).to_pydatetime()
            except Exception:
                order_date = datetime.utcnow()
        else:
            order_date = datetime.utcnow()

        records.append(
            {
                "order_id": str(row["order_id"]),
                "user_id": unique_id if unique_id else None,
                "product_id": str(row["product_id"]) if pd.notna(row.get("product_id")) else None,
                "seller_id": str(row["seller_id"]) if pd.notna(row.get("seller_id")) else None,
                "order_total_usd": round(price * BRL_TO_USD, 4),
                "freight_value_usd": round(freight * BRL_TO_USD, 4),
                "order_status": str(row.get("order_status", "unknown")).strip(),
                "created_at": order_date,
            }
        )

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        for chunk_start in range(0, len(records), 2000):
            chunk = records[chunk_start : chunk_start + 2000]
            session.bulk_insert_mappings(FactOrders, chunk)
            session.commit()
            logger.info("  fact_orders: inserted rows %d–%d", chunk_start, chunk_start + len(chunk))
    logger.info("fact_orders loaded: %d rows.", len(records))


def load_dim_reviews(reviews_df: pd.DataFrame, engine) -> None:
    """Load dim_reviews from olist_order_reviews_dataset.csv."""
    logger.info("Loading dim_reviews (%d rows)...", len(reviews_df))
    # Deduplicate by review_id
    reviews_dedup = reviews_df.drop_duplicates(subset=["review_id"])
    records = [
        {
            "review_id": str(row["review_id"]),
            "order_id": str(row["order_id"]),
            "review_score": int(row["review_score"]) if pd.notna(row.get("review_score")) else None,
            "review_comment": str(row["review_comment_message"]) if pd.notna(row.get("review_comment_message")) else None,
        }
        for _, row in reviews_dedup.iterrows()
    ]

    # Filter to only orders that exist in fact_orders to maintain FK integrity
    from sqlalchemy import text

    with get_engine().connect() as conn:
        existing_orders = {
            row[0] for row in conn.execute(text("SELECT order_id FROM fact_orders"))
        }
    records = [r for r in records if r["order_id"] in existing_orders]

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        for chunk_start in range(0, len(records), 2000):
            chunk = records[chunk_start : chunk_start + 2000]
            session.bulk_insert_mappings(DimReviews, chunk)
            session.commit()
    logger.info("dim_reviews loaded: %d reviews.", len(records))


def seed() -> None:
    """Main entry point: create schema, load all dimension and fact tables."""
    maybe_download_from_kaggle()

    if not check_csv_files():
        sys.exit(1)

    engine = get_engine()
    logger.info("Creating database schema...")
    Base.metadata.create_all(engine)

    # Check if already seeded
    inspector = inspect(engine)
    if inspector.has_table("fact_orders"):
        from sqlalchemy import text as sqtext

        with engine.connect() as conn:
            count = conn.execute(sqtext("SELECT COUNT(*) FROM fact_orders")).scalar()
            if count and count > 0:
                logger.info("Database already seeded (%d fact_orders rows). Skipping.", count)
                return

    logger.info("Reading CSV files from %s...", RAW_DIR)
    orders_df = pd.read_csv(RAW_DIR / CSV_FILES["orders"])
    items_df = pd.read_csv(RAW_DIR / CSV_FILES["order_items"])
    customers_df = pd.read_csv(RAW_DIR / CSV_FILES["customers"])
    products_df = pd.read_csv(RAW_DIR / CSV_FILES["products"])
    sellers_df = pd.read_csv(RAW_DIR / CSV_FILES["sellers"])
    geo_df = pd.read_csv(RAW_DIR / CSV_FILES["geolocation"])
    reviews_df = pd.read_csv(RAW_DIR / CSV_FILES["reviews"])

    # Load product category translations if available
    translation_path = RAW_DIR / "product_category_name_translation.csv"
    if translation_path.exists():
        translations = pd.read_csv(translation_path)
        products_df = products_df.merge(translations, on="product_category_name", how="left")

    # Load dimensions first (referenced by foreign keys)
    load_dim_users(customers_df, engine)
    load_dim_products(products_df, engine)
    load_dim_sellers(sellers_df, engine)
    load_dim_geography(geo_df, engine)

    # Load fact table
    load_fact_orders(orders_df, items_df, customers_df, engine)

    # Load review dimension last (needs fact_orders FK)
    load_dim_reviews(reviews_df, engine)

    logger.info("✅ Seed complete!")


if __name__ == "__main__":
    seed()
