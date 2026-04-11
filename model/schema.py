# INTERN NOTE: Star schema rationale
# A star schema separates measurable business events (facts) from
# descriptive attributes (dimensions). fact_orders is the central table
# holding numeric metrics (revenue, freight) while dim_* tables hold
# slow-changing descriptors (user city, product category, seller location).
# This makes aggregation queries fast: GROUP BY on a dim column, SUM on a
# fact column, joined by surrogate keys. It also mirrors how analysts think:
# "revenue BY category" = fact JOIN dim_products GROUP BY category_name.
# The query_log table is a meta-table used for observability, not analytics.

from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class FactOrders(Base):
    __tablename__ = "fact_orders"

    order_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("dim_users.user_id"), nullable=True, index=True)
    product_id = Column(String(64), ForeignKey("dim_products.product_id"), nullable=True, index=True)
    seller_id = Column(String(64), ForeignKey("dim_sellers.seller_id"), nullable=True, index=True)
    order_total_usd = Column(Numeric(12, 2), nullable=False, default=0)
    freight_value_usd = Column(Numeric(12, 2), nullable=False, default=0)
    order_status = Column(String(32), nullable=False, default="unknown")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())

    user = relationship("DimUsers", back_populates="orders")
    product = relationship("DimProducts", back_populates="orders")
    seller = relationship("DimSellers", back_populates="orders")
    review = relationship("DimReviews", back_populates="order", uselist=False)


class DimUsers(Base):
    __tablename__ = "dim_users"

    user_id = Column(String(64), primary_key=True)
    city = Column(String(128), nullable=True)
    state = Column(String(8), nullable=True)
    signup_country_code = Column(String(8), nullable=True, default="BR")
    is_active_member = Column(Boolean, nullable=False, default=True)

    orders = relationship("FactOrders", back_populates="user")


class DimProducts(Base):
    __tablename__ = "dim_products"

    product_id = Column(String(64), primary_key=True)
    category_name = Column(String(128), nullable=True)
    photos_qty = Column(Integer, nullable=True, default=0)

    orders = relationship("FactOrders", back_populates="product")


class DimSellers(Base):
    __tablename__ = "dim_sellers"

    seller_id = Column(String(64), primary_key=True)
    seller_city = Column(String(128), nullable=True)
    seller_state = Column(String(8), nullable=True)

    orders = relationship("FactOrders", back_populates="seller")


class DimGeography(Base):
    __tablename__ = "dim_geography"

    geo_id = Column(Integer, primary_key=True, autoincrement=True)
    zip_code_prefix = Column(String(16), nullable=False, index=True)
    city = Column(String(128), nullable=True)
    state = Column(String(8), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    __table_args__ = (UniqueConstraint("zip_code_prefix", "city", name="uq_geo_zip_city"),)


class DimReviews(Base):
    __tablename__ = "dim_reviews"

    review_id = Column(String(64), primary_key=True)
    order_id = Column(String(64), ForeignKey("fact_orders.order_id"), nullable=False, index=True, unique=True)
    review_score = Column(Integer, nullable=True)
    review_comment = Column(Text, nullable=True)

    order = relationship("FactOrders", back_populates="review")


class QueryLog(Base):
    __tablename__ = "query_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    tables_used = Column(Text, nullable=True)  # comma-separated list
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
