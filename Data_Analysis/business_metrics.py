"""Business metric calculations for e-commerce sales analysis.

Every function here is pure: it takes already-loaded, already-filtered
DataFrames as input (see ``data_loader.py`` for loading and filtering) and
returns a computed metric. None of these functions read files, filter by
date, or hard-code a specific year -- that keeps them reusable across any
period or any dataset with the same shape.

Growth-rate functions return a fraction (e.g. ``-0.0246`` for a 2.46%
decline), not a pre-formatted percentage, so callers can format or threshold
them however is appropriate for their context.
"""


# ---------------------------------------------------------------------------
# Revenue metrics
# ---------------------------------------------------------------------------

def total_revenue(sales, price_column="price"):
    """Sum of ``price_column`` across all order line items in ``sales``."""
    return sales[price_column].sum()


def revenue_growth_rate(current_sales, comparison_sales, price_column="price"):
    """Fractional change in total revenue between two periods.

    Returns
    -------
    float
        e.g. -0.0246 for a 2.46% decline relative to ``comparison_sales``.
    """
    current_revenue = total_revenue(current_sales, price_column)
    comparison_revenue = total_revenue(comparison_sales, price_column)
    return (current_revenue - comparison_revenue) / comparison_revenue


def monthly_revenue_trend(sales, price_column="price", month_column="purchase_month"):
    """Total revenue for each calendar month present in ``sales``.

    Returns
    -------
    pandas.Series
        Indexed by month number, sorted ascending.
    """
    return sales.groupby(month_column)[price_column].sum().sort_index()


def monthly_revenue_series(sales, date_column="order_purchase_timestamp", price_column="price"):
    """Total revenue per calendar month, in chronological order.

    Unlike ``monthly_revenue_trend`` (which buckets by month-of-year and so
    only makes sense within a single year), this buckets by year-month and
    so also works for a period that spans a year boundary -- the natural
    case when filtering by an arbitrary date range.

    Returns
    -------
    pandas.Series
        Indexed by ``pandas.Period`` (monthly frequency), sorted ascending.
    """
    year_months = sales[date_column].dt.to_period("M")
    return sales.groupby(year_months)[price_column].sum().sort_index()


def average_month_over_month_growth(monthly_revenue):
    """Mean of the month-over-month percent changes in a revenue series.

    Parameters
    ----------
    monthly_revenue : pandas.Series
        Typically the output of ``monthly_revenue_trend``.
    """
    return monthly_revenue.pct_change().mean()


# ---------------------------------------------------------------------------
# Order metrics
# ---------------------------------------------------------------------------

def average_order_value(sales, order_id_column="order_id", price_column="price"):
    """Mean order value: line-item prices summed per order, then averaged."""
    return sales.groupby(order_id_column)[price_column].sum().mean()


def order_value_growth_rate(current_sales, comparison_sales):
    """Fractional change in average order value between two periods."""
    current_aov = average_order_value(current_sales)
    comparison_aov = average_order_value(comparison_sales)
    return (current_aov - comparison_aov) / comparison_aov


def total_orders(sales, order_id_column="order_id"):
    """Count of distinct orders represented in ``sales``."""
    return sales[order_id_column].nunique()


def order_count_growth_rate(current_sales, comparison_sales):
    """Fractional change in distinct order count between two periods."""
    current_count = total_orders(current_sales)
    comparison_count = total_orders(comparison_sales)
    return (current_count - comparison_count) / comparison_count


def order_status_distribution(orders):
    """Share of orders in each ``order_status`` value.

    Parameters
    ----------
    orders : pandas.DataFrame
        An orders table (not the merged sales table), already filtered to
        the period of interest.

    Returns
    -------
    pandas.Series
        Proportions summing to 1, indexed by order status.
    """
    return orders["order_status"].value_counts(normalize=True)


# ---------------------------------------------------------------------------
# Product / geographic metrics
# ---------------------------------------------------------------------------

def revenue_by_category(sales, products, price_column="price"):
    """Total revenue per product category, descending.

    Parameters
    ----------
    sales : pandas.DataFrame
        Must include ``product_id`` and ``price_column``.
    products : pandas.DataFrame
        Must include ``product_id`` and ``product_category_name``.

    Returns
    -------
    pandas.Series
        Indexed by product category, sorted descending by revenue.
    """
    merged = products[["product_id", "product_category_name"]].merge(
        sales[["product_id", price_column]], on="product_id"
    )
    return merged.groupby("product_category_name")[price_column].sum().sort_values(
        ascending=False
    )


def revenue_by_state(sales, orders, customers, price_column="price"):
    """Total revenue per customer state, descending.

    Parameters
    ----------
    sales : pandas.DataFrame
        Must include ``order_id`` and ``price_column``.
    orders : pandas.DataFrame
        Must include ``order_id`` and ``customer_id``.
    customers : pandas.DataFrame
        Must include ``customer_id`` and ``customer_state``.

    Returns
    -------
    pandas.DataFrame
        Columns: ``customer_state``, ``price_column``. Sorted descending.
    """
    sales_with_customer = sales[["order_id", price_column]].merge(
        orders[["order_id", "customer_id"]], on="order_id"
    )
    sales_with_state = sales_with_customer.merge(
        customers[["customer_id", "customer_state"]], on="customer_id"
    )
    return (
        sales_with_state.groupby("customer_state")[price_column]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )


# ---------------------------------------------------------------------------
# Customer experience metrics (delivery speed, reviews)
# ---------------------------------------------------------------------------

def average_delivery_time(sales, delivery_speed_column="delivery_speed_days"):
    """Mean delivery time in days, computed once per distinct order."""
    return sales.drop_duplicates(subset="order_id")[delivery_speed_column].mean()


def categorize_delivery_speed(days, bins, labels):
    """Bucket a delivery-time value (in days) into a labeled speed tier.

    Parameters
    ----------
    days : int or float
        Delivery time in days.
    bins : sequence of int
        Inclusive upper bound for each tier except the last, e.g. ``[3, 7]``
        groups ``days <= 3`` into ``labels[0]``, ``days <= 7`` into
        ``labels[1]``, and anything higher into ``labels[-1]``.
    labels : sequence of str
        Must have ``len(bins) + 1`` entries.

    Returns
    -------
    str
    """
    for upper_bound, label in zip(bins, labels):
        if days <= upper_bound:
            return label
    return labels[-1]


def review_score_by_delivery_speed(
    sales_with_reviews,
    delivery_speed_column="delivery_speed_days",
    review_score_column="review_score",
):
    """Mean review score for each distinct delivery-speed value, in days.

    Returns
    -------
    pandas.DataFrame
        Columns: ``delivery_speed_column``, ``review_score_column``.
    """
    distinct = sales_with_reviews.drop_duplicates(subset="order_id")
    return (
        distinct.groupby(delivery_speed_column)[review_score_column]
        .mean()
        .reset_index()
    )


def review_score_by_delivery_tier(
    sales_with_reviews,
    bins,
    labels,
    delivery_speed_column="delivery_speed_days",
    review_score_column="review_score",
):
    """Mean review score grouped into delivery-speed tiers.

    See ``categorize_delivery_speed`` for how ``bins`` / ``labels`` define
    the tiers.

    Returns
    -------
    pandas.DataFrame
        Columns: ``delivery_tier``, ``review_score_column``.
    """
    distinct = sales_with_reviews.drop_duplicates(subset="order_id").copy()
    distinct["delivery_tier"] = distinct[delivery_speed_column].apply(
        lambda days: categorize_delivery_speed(days, bins, labels)
    )
    return distinct.groupby("delivery_tier")[review_score_column].mean().reset_index()


def average_review_score(sales_with_reviews, review_score_column="review_score"):
    """Mean review score, computed once per distinct order."""
    return sales_with_reviews.drop_duplicates(subset="order_id")[review_score_column].mean()


def review_score_distribution(sales_with_reviews, review_score_column="review_score"):
    """Share of distinct orders at each review score.

    Returns
    -------
    pandas.Series
        Proportions summing to 1, indexed by review score, sorted ascending.
    """
    distinct = sales_with_reviews.drop_duplicates(subset="order_id")
    return distinct[review_score_column].value_counts(normalize=True).sort_index()
