"""E-Commerce Sales Dashboard.

A Streamlit dashboard over the same data and metrics as EDA_Refactored.ipynb.
All data loading lives in data_loader.py, all metric calculations live in
business_metrics.py, and all formatting/chart-building lives in
dashboard_components.py -- this file only wires the year/month filter to
those layers and lays out the page.
"""

import calendar
import math

import pandas as pd
import streamlit as st

import business_metrics as bm
import dashboard_components as dc
import data_loader as dl

DATA_DIR = "ecommerce_data"
DEFAULT_YEAR = 2023
MONTH_NAMES = ["All Months"] + [calendar.month_name[m] for m in range(1, 13)]

# Delivery-speed tiers used in the satisfaction chart. DELIVERY_SPEED_BINS[i]
# is the inclusive upper bound (in days) of DELIVERY_SPEED_LABELS[i]; the
# final label catches everything above the last bin.
DELIVERY_SPEED_BINS = [3, 7]
DELIVERY_SPEED_LABELS = ["1-3 days", "4-7 days", "8+ days"]

PLOTLY_CONFIG = {"displaylogo": False, "displayModeBar": "hover"}


@st.cache_data
def load_data(data_dir):
    """Load and prepare all source tables, and build the delivered-sales base table."""
    datasets = dl.load_datasets(data_dir)
    orders = dl.prepare_orders(datasets["orders"])
    reviews = dl.prepare_reviews(datasets["reviews"])

    sales = dl.build_sales_dataset(datasets["order_items"], orders)
    sales_delivered = dl.filter_delivered(sales)

    return {
        "orders": orders,
        "reviews": reviews,
        "products": datasets["products"],
        "customers": datasets["customers"],
        "sales_delivered": sales_delivered,
    }


def period_label(year, month):
    """Human-readable label for a year or a single year-month."""
    if month is None:
        return str(year)
    return f"{calendar.month_name[month]} {year}"


def pct_change(current, previous):
    """Fractional change between two scalars, or None if not computable."""
    if previous is None or (isinstance(previous, float) and (math.isnan(previous) or previous == 0)):
        return None
    if previous == 0:
        return None
    if current is None or (isinstance(current, float) and math.isnan(current)):
        return None
    return (current - previous) / previous


def safe_growth(growth_fn, current_sales, previous_sales):
    """Call a business_metrics growth function, guarding empty periods."""
    if len(current_sales) == 0 or len(previous_sales) == 0:
        return None
    value = growth_fn(current_sales, previous_sales)
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    return value


def build_period_dataset(sales_delivered, orders, reviews, year, month):
    """Scope the delivered-sales and orders tables to a year/month, and enrich
    with delivery speed and review scores."""
    sales_period = dl.filter_by_year_month(sales_delivered, year=year, month=month)
    orders_period = dl.filter_by_year_month(orders, year=year, month=month)
    sales_period = dl.add_delivery_speed(sales_period)
    sales_period_reviewed = dl.attach_reviews(sales_period, reviews)
    return sales_period, orders_period, sales_period_reviewed


def main():
    st.set_page_config(page_title="E-Commerce Sales Dashboard", layout="wide")
    st.markdown(dc.dashboard_css(), unsafe_allow_html=True)

    data = load_data(DATA_DIR)
    orders, reviews = data["orders"], data["reviews"]
    products, customers = data["products"], data["customers"]
    sales_delivered = data["sales_delivered"]

    available_years = sorted(sales_delivered["purchase_year"].unique().tolist())
    default_year_index = (
        available_years.index(DEFAULT_YEAR) if DEFAULT_YEAR in available_years else len(available_years) - 1
    )

    # ---- Header: title (left) + year/month filter (right) --------------------
    header_left, header_right = st.columns([3, 2])
    with header_left:
        st.title("E-Commerce Sales Dashboard")
        st.markdown(
            "<p style='color:#52514e;margin-top:-10px;'>"
            "Revenue, product, geographic, and customer-experience performance</p>",
            unsafe_allow_html=True,
        )
    with header_right:
        year_col, month_col = st.columns(2)
        selected_year = year_col.selectbox("Year", options=available_years, index=default_year_index)
        selected_month_name = month_col.selectbox("Month", options=MONTH_NAMES, index=0)
        selected_month = None if selected_month_name == "All Months" else MONTH_NAMES.index(selected_month_name)

    comparison_year = selected_year - 1
    current_label = period_label(selected_year, selected_month)
    previous_label = period_label(comparison_year, selected_month)

    sales_current, orders_current, sales_current_reviewed = build_period_dataset(
        sales_delivered, orders, reviews, selected_year, selected_month
    )
    sales_previous, _orders_previous, sales_previous_reviewed = build_period_dataset(
        sales_delivered, orders, reviews, comparison_year, selected_month
    )

    if len(sales_current) == 0:
        st.warning(f"No delivered orders in {current_label}. Pick a different year or month.")
        st.stop()

    # ---- Metric calculations -----------------------------------------------
    revenue = bm.total_revenue(sales_current)
    revenue_growth = safe_growth(bm.revenue_growth_rate, sales_current, sales_previous)

    monthly_revenue_current = bm.monthly_revenue_series(sales_current)
    monthly_revenue_previous = bm.monthly_revenue_series(sales_previous)
    mom_growth = (
        bm.average_month_over_month_growth(monthly_revenue_current)
        if len(monthly_revenue_current) > 1
        else None
    )
    if mom_growth is not None and pd.isna(mom_growth):
        mom_growth = None

    aov = bm.average_order_value(sales_current)
    aov_growth = safe_growth(bm.order_value_growth_rate, sales_current, sales_previous)

    order_count = bm.total_orders(sales_current)
    order_growth = safe_growth(bm.order_count_growth_rate, sales_current, sales_previous)

    category_revenue = bm.revenue_by_category(sales_current, products)
    state_revenue = bm.revenue_by_state(sales_current, orders, customers)

    avg_delivery_days = (
        bm.average_delivery_time(sales_current_reviewed) if len(sales_current_reviewed) else float("nan")
    )
    avg_delivery_days_previous = (
        bm.average_delivery_time(sales_previous_reviewed) if len(sales_previous_reviewed) else float("nan")
    )
    delivery_growth = pct_change(avg_delivery_days, avg_delivery_days_previous)

    avg_review = (
        bm.average_review_score(sales_current_reviewed) if len(sales_current_reviewed) else float("nan")
    )
    review_by_tier = (
        bm.review_score_by_delivery_tier(sales_current_reviewed, DELIVERY_SPEED_BINS, DELIVERY_SPEED_LABELS)
        if len(sales_current_reviewed)
        else pd.DataFrame(columns=["delivery_tier", "review_score"])
    )

    # ---- KPI row -------------------------------------------------------------
    kpi_cols = st.columns(4)
    dc.render_trend_card(kpi_cols[0], "Total Revenue", dc.format_currency_full(revenue), revenue_growth)
    dc.render_growth_card(kpi_cols[1], "Monthly Growth", mom_growth)
    dc.render_trend_card(kpi_cols[2], "Average Order Value", dc.format_currency_full(aov), aov_growth)
    dc.render_trend_card(kpi_cols[3], "Total Orders", dc.format_count(order_count), order_growth)

    st.write("")

    # ---- Charts grid (2x2) ----------------------------------------------------
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        fig = dc.build_revenue_trend_chart(
            monthly_revenue_current, monthly_revenue_previous, current_label, previous_label
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    with row1_col2:
        fig = dc.build_category_bar_chart(category_revenue, top_n=10)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        fig = dc.build_state_choropleth(state_revenue)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    with row2_col2:
        fig = dc.build_satisfaction_chart(review_by_tier)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    st.write("")

    # ---- Bottom row -------------------------------------------------------------
    bottom_col1, bottom_col2 = st.columns(2)
    with bottom_col1:
        delivery_text = "N/A" if math.isnan(avg_delivery_days) else f"{avg_delivery_days:.2f} days"
        dc.render_trend_card(
            bottom_col1, "Average Delivery Time", delivery_text, delivery_growth, positive_is_good=False
        )
    with bottom_col2:
        dc.render_review_card(bottom_col2, avg_review)

    st.caption(
        f"Analysis period: {current_label}  |  Compared against: {previous_label}  |  "
        f"{dc.format_count(order_count)} delivered orders in the selected period."
    )


if __name__ == "__main__":
    main()
