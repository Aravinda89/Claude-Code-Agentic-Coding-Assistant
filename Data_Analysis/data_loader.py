"""Loading and preparation utilities for the e-commerce sales datasets.

This module is responsible for reading the raw CSV files, parsing dates,
merging them into an analysis-ready sales table, and filtering that table
to a configurable year/month. It intentionally contains no business-metric
calculations -- those live in ``business_metrics.py``.

Typical usage:

    from data_loader import load_datasets, prepare_orders, prepare_reviews, \\
        build_sales_dataset, filter_delivered, filter_by_year_month, \\
        add_delivery_speed, attach_reviews

    datasets = load_datasets("ecommerce_data")
    orders = prepare_orders(datasets["orders"])
    reviews = prepare_reviews(datasets["reviews"])

    sales = build_sales_dataset(datasets["order_items"], orders)
    sales_delivered = filter_delivered(sales)
    sales_2023 = filter_by_year_month(sales_delivered, year=2023)
"""

from pathlib import Path

import pandas as pd

# Columns that hold datetime values in their raw string form and need parsing.
ORDER_DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
REVIEW_DATE_COLUMNS = ["review_creation_date", "review_answer_timestamp"]

# Columns pulled from order_items / orders when building the sales table.
SALES_ORDER_ITEM_COLUMNS = ["order_id", "order_item_id", "product_id", "price"]
SALES_ORDER_COLUMNS = [
    "order_id",
    "order_status",
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "purchase_year",
    "purchase_month",
]

DATASET_FILENAMES = {
    "orders": "orders_dataset.csv",
    "order_items": "order_items_dataset.csv",
    "products": "products_dataset.csv",
    "customers": "customers_dataset.csv",
    "reviews": "order_reviews_dataset.csv",
}


def load_datasets(data_dir):
    """Read the raw e-commerce CSV files into a dict of DataFrames.

    Parameters
    ----------
    data_dir : str or Path
        Directory containing the e-commerce CSV files.

    Returns
    -------
    dict[str, pandas.DataFrame]
        Keys: "orders", "order_items", "products", "customers", "reviews".
    """
    data_dir = Path(data_dir)
    return {
        name: pd.read_csv(data_dir / filename)
        for name, filename in DATASET_FILENAMES.items()
    }


def parse_date_columns(df, columns):
    """Return a copy of ``df`` with the given columns converted to datetime.

    Columns not present in ``df`` are silently skipped, so the same column
    list can be reused across datasets with slightly different schemas.
    """
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column])
    return df


def prepare_orders(orders):
    """Parse order date columns and add ``purchase_year`` / ``purchase_month``.

    These two columns are what the rest of the pipeline filters on, so this
    step should run once, right after loading, before any merging.
    """
    orders = parse_date_columns(orders, ORDER_DATE_COLUMNS)
    orders["purchase_year"] = orders["order_purchase_timestamp"].dt.year
    orders["purchase_month"] = orders["order_purchase_timestamp"].dt.month
    return orders


def prepare_reviews(reviews):
    """Parse review date columns."""
    return parse_date_columns(reviews, REVIEW_DATE_COLUMNS)


def build_sales_dataset(order_items, orders):
    """Merge order line items with order-level status and date fields.

    The result has one row per order line item and is the base table that
    revenue, product, geographic, and customer-experience metrics are all
    computed from. ``orders`` must already have been run through
    ``prepare_orders`` (so ``purchase_year`` / ``purchase_month`` exist).

    Parameters
    ----------
    order_items : pandas.DataFrame
    orders : pandas.DataFrame

    Returns
    -------
    pandas.DataFrame
    """
    return order_items[SALES_ORDER_ITEM_COLUMNS].merge(
        orders[SALES_ORDER_COLUMNS], on="order_id", how="inner"
    )


def filter_delivered(sales):
    """Return only line items belonging to orders with status 'delivered'."""
    return sales[sales["order_status"] == "delivered"].copy()


def filter_by_year_month(df, year, month=None, date_column="order_purchase_timestamp"):
    """Filter a DataFrame to a given purchase year, and optionally a month.

    This is the single entry point for scoping any analysis to a period --
    changing ``year`` / ``month`` here is enough to re-run the whole notebook
    against a different window, with no other code changes required.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain ``date_column`` as a datetime dtype.
    year : int
        Calendar year to keep.
    month : int, optional
        Calendar month (1-12) to keep. If ``None`` (default), the whole
        year is returned.
    date_column : str, default "order_purchase_timestamp"
        Column to filter on.

    Returns
    -------
    pandas.DataFrame
    """
    mask = df[date_column].dt.year == year
    if month is not None:
        mask &= df[date_column].dt.month == month
    return df[mask].copy()


def add_delivery_speed(sales):
    """Add a ``delivery_speed_days`` column: days from purchase to delivery.

    Requires ``order_purchase_timestamp`` and ``order_delivered_customer_date``
    to be datetime columns. Rows for undelivered orders will get ``NaN``.
    """
    sales = sales.copy()
    sales["delivery_speed_days"] = (
        sales["order_delivered_customer_date"] - sales["order_purchase_timestamp"]
    ).dt.days
    return sales


def attach_reviews(sales, reviews):
    """Inner-join review scores onto the sales table by ``order_id``.

    Orders without a review are dropped, matching the original analysis
    (which only looked at review scores where a review existed).
    """
    return sales.merge(reviews[["order_id", "review_score"]], on="order_id", how="inner")
