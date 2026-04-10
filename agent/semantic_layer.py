# INTERN NOTE: Semantic layer concept
# Raw table/column names like "order_total_usd" or "is_active_member" are
# meaningful to engineers but ambiguous to LLMs without business context.
# The semantic layer maps each column to its business meaning, valid value
# ranges, and usage rules. When injected into the LLM prompt, it dramatically
# reduces hallucinated SQL (wrong aggregation functions, wrong join keys).
# Think of it as a "data dictionary" that the LLM reads before writing SQL.
# In production, this can be extended with ownership, SLAs, and PII tags.

from typing import Any

SEMANTIC_SCHEMA: list[dict[str, Any]] = [
    {
        "table_name": "fact_orders",
        "description": (
            "Central fact table. Each row is one order-item event in the Olist marketplace. "
            "Use this table for all revenue, freight, and order-status analyses. "
            "Always join to dimension tables via the appropriate *_id foreign key."
        ),
        "columns": [
            {
                "name": "order_id",
                "description": (
                    "Unique identifier for a customer order. "
                    "An order can appear multiple times if it contains multiple items."
                ),
            },
            {
                "name": "user_id",
                "description": (
                    "Foreign key to dim_users. Identifies the purchasing customer."
                ),
            },
            {
                "name": "product_id",
                "description": (
                    "Foreign key to dim_products. Identifies the specific product purchased."
                ),
            },
            {
                "name": "seller_id",
                "description": (
                    "Foreign key to dim_sellers. Identifies the seller who fulfilled the item."
                ),
            },
            {
                "name": "order_total_usd",
                "description": (
                    "Final post-tax revenue in USD for this line item. "
                    "Always use this for GMV (Gross Merchandise Value) calculations. "
                    "Never use freight_value_usd as a revenue proxy."
                ),
            },
            {
                "name": "freight_value_usd",
                "description": (
                    "Shipping cost in USD paid by the customer for this item. "
                    "Use for logistics cost analysis, not for revenue."
                ),
            },
            {
                "name": "order_status",
                "description": (
                    "Current fulfillment status. Values: delivered, shipped, canceled, "
                    "processing, invoiced, unavailable, approved, created. "
                    "For completed revenue, filter WHERE order_status = 'delivered'."
                ),
            },
            {
                "name": "created_at",
                "description": (
                    "Timestamp when the order was placed. Use for time-series and date-range queries. "
                    "Use strftime('%Y-%m', created_at) to group by month in SQLite."
                ),
            },
        ],
    },
    {
        "table_name": "dim_users",
        "description": (
            "Customer dimension. One row per unique customer. "
            "Use for geographic segmentation, cohort analysis, and active-member filtering."
        ),
        "columns": [
            {
                "name": "user_id",
                "description": "Primary key. Unique customer identifier. Matches fact_orders.user_id.",
            },
            {
                "name": "city",
                "description": "Customer's billing city (Brazilian city name in Portuguese).",
            },
            {
                "name": "state",
                "description": "Brazilian state abbreviation, e.g. SP, RJ, MG. Use for state-level analysis.",
            },
            {
                "name": "signup_country_code",
                "description": (
                    "ISO 3166-1 alpha-2 country code. Almost always 'BR' for Brazil. "
                    "Use for international expansion analysis."
                ),
            },
            {
                "name": "is_active_member",
                "description": (
                    "Boolean flag. True if the customer has placed an order in the last 6 months. "
                    "Use WHERE is_active_member = 1 to filter to engaged users."
                ),
            },
        ],
    },
    {
        "table_name": "dim_products",
        "description": (
            "Product dimension. One row per unique product SKU. "
            "Use for category performance, product catalog, and merchandising analysis."
        ),
        "columns": [
            {
                "name": "product_id",
                "description": "Primary key. Unique product identifier. Matches fact_orders.product_id.",
            },
            {
                "name": "category_name",
                "description": (
                    "English product category label, e.g. 'electronics', 'furniture', 'health_beauty'. "
                    "Use for category-level revenue roll-ups."
                ),
            },
            {
                "name": "photos_qty",
                "description": (
                    "Number of product photos in the listing. "
                    "Higher values correlate with higher conversion rates."
                ),
            },
        ],
    },
    {
        "table_name": "dim_sellers",
        "description": (
            "Seller dimension. One row per registered Olist seller. "
            "Use for seller performance, geographic distribution, and supply analysis."
        ),
        "columns": [
            {
                "name": "seller_id",
                "description": "Primary key. Unique seller identifier. Matches fact_orders.seller_id.",
            },
            {
                "name": "seller_city",
                "description": "City where the seller is registered (Brazilian city name).",
            },
            {
                "name": "seller_state",
                "description": "Brazilian state abbreviation for the seller's registered address.",
            },
        ],
    },
    {
        "table_name": "dim_geography",
        "description": (
            "Geolocation lookup table mapping Brazilian zip code prefixes to cities, "
            "states, and lat/lng coordinates. Use for distance calculations and map visualizations. "
            "Join to dim_users or dim_sellers via city/state, not directly via foreign key."
        ),
        "columns": [
            {
                "name": "geo_id",
                "description": "Surrogate primary key. Auto-incremented integer.",
            },
            {
                "name": "zip_code_prefix",
                "description": "First 5 digits of a Brazilian CEP (postal code).",
            },
            {
                "name": "city",
                "description": "City name corresponding to this zip prefix.",
            },
            {
                "name": "state",
                "description": "State abbreviation corresponding to this zip prefix.",
            },
            {
                "name": "lat",
                "description": "Latitude of the zip code centroid (decimal degrees, WGS84).",
            },
            {
                "name": "lng",
                "description": "Longitude of the zip code centroid (decimal degrees, WGS84).",
            },
        ],
    },
    {
        "table_name": "dim_reviews",
        "description": (
            "Customer review dimension. One row per review submitted. "
            "Use for NPS analysis, satisfaction scoring, and sentiment filtering. "
            "Join to fact_orders via order_id."
        ),
        "columns": [
            {
                "name": "review_id",
                "description": "Primary key. Unique review identifier.",
            },
            {
                "name": "order_id",
                "description": "Foreign key to fact_orders. Links the review to its order.",
            },
            {
                "name": "review_score",
                "description": (
                    "Customer satisfaction score from 1 (worst) to 5 (best). "
                    "Use AVG(review_score) for mean satisfaction, COUNT(*) WHERE review_score <= 2 for complaint rate."
                ),
            },
            {
                "name": "review_comment",
                "description": "Free-text comment left by the customer. May be NULL.",
            },
        ],
    },
]
