"""Presentation layer for the Streamlit dashboard: formatting, card
rendering, and Plotly chart builders.

This module contains no data loading and no metric calculations -- it only
turns numbers that `business_metrics.py` already computed into formatted
text, styled HTML cards, and Plotly figures. Every chart and card in the
dashboard shares the same blue color scheme defined here.
"""

import math

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------------------------
# Color scheme (shared across every chart and card)
# ---------------------------------------------------------------------------
BLUE = "#2a78d6"
BLUE_LIGHT = "#86b6ef"
GRID_COLOR = "#e1e0d9"
INK = "#0b0b0b"
MUTED_INK = "#52514e"
CHART_SURFACE = "#fcfcfb"

# Light-to-dark sequential blue ramp: lower values render lighter.
BLUE_SEQUENTIAL = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
    "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]

# Fixed status colors -- reserved for trend direction, never reused as a
# series color.
POSITIVE_COLOR = "#006300"
NEGATIVE_COLOR = "#d03b3b"
NEUTRAL_COLOR = "#898781"

CHART_HEIGHT = 420
CARD_HEIGHT_PX = 152


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_currency_short(value):
    """Format a dollar amount using K / M / B suffixes, e.g. "$300K", "$2M"."""
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        magnitude, suffix = 1_000_000_000, "B"
    elif abs_value >= 1_000_000:
        magnitude, suffix = 1_000_000, "M"
    elif abs_value >= 1_000:
        magnitude, suffix = 1_000, "K"
    else:
        return f"{sign}${abs_value:,.0f}"

    scaled = abs_value / magnitude
    text = f"{scaled:.1f}".rstrip("0").rstrip(".")
    return f"{sign}${text}{suffix}"


def format_currency_full(value):
    """Format a dollar amount with full precision, e.g. "$3,360,294.74"."""
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def format_count(value):
    """Format an integer count with thousands separators, e.g. "4,635"."""
    return f"{value:,.0f}"


def format_percent(fraction, decimals=2):
    """Format a growth fraction as a signed percentage, e.g. "+2.46%"."""
    return f"{fraction * 100:+.{decimals}f}%"


def nice_ticks(max_value, count=5):
    """Generate round-number axis tick values from 0 to at least ``max_value``.

    Mirrors what matplotlib/Plotly auto-ticking does internally, but as an
    explicit list so tick labels can be rendered through
    ``format_currency_short`` instead of Plotly's default numeric format.
    """
    if max_value is None or max_value <= 0 or math.isnan(max_value):
        return [0]

    raw_step = max_value / count
    magnitude = 10 ** math.floor(math.log10(raw_step))
    residual = raw_step / magnitude
    if residual > 5:
        step = 10 * magnitude
    elif residual > 2:
        step = 5 * magnitude
    elif residual > 1:
        step = 2 * magnitude
    else:
        step = magnitude

    ticks = []
    value = 0.0
    while value <= max_value + step:
        ticks.append(value)
        value += step
    return ticks


# ---------------------------------------------------------------------------
# Card styling and rendering
# ---------------------------------------------------------------------------

def dashboard_css():
    """Global CSS for the KPI/stat cards, injected once via st.markdown."""
    return f"""
    <style>
    .kpi-card {{
        background-color: {CHART_SURFACE};
        border: 1px solid {GRID_COLOR};
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(11, 11, 11, 0.06);
        height: {CARD_HEIGHT_PX}px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 4px;
    }}
    .kpi-label {{
        font-size: 0.8rem;
        font-weight: 600;
        color: {MUTED_INK};
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin: 0;
    }}
    .kpi-value {{
        font-size: 1.9rem;
        font-weight: 700;
        color: {INK};
        line-height: 1.2;
        margin: 0;
    }}
    .kpi-value-large {{
        font-size: 2.3rem;
    }}
    .kpi-value-positive {{ color: {POSITIVE_COLOR}; }}
    .kpi-value-negative {{ color: {NEGATIVE_COLOR}; }}
    .kpi-delta {{
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0;
    }}
    .kpi-delta-positive {{ color: {POSITIVE_COLOR}; }}
    .kpi-delta-negative {{ color: {NEGATIVE_COLOR}; }}
    .kpi-delta-neutral {{ color: {NEUTRAL_COLOR}; font-weight: 500; }}
    .kpi-stars {{
        font-size: 1.4rem;
        color: #c98500;
        letter-spacing: 0.1em;
        margin: 0;
    }}
    .kpi-subtitle {{
        font-size: 0.85rem;
        color: {MUTED_INK};
        margin: 0;
    }}
    </style>
    """


def _delta_html(growth_fraction, decimals, positive_is_good=True, comparison_note="vs previous period"):
    if growth_fraction is None or (isinstance(growth_fraction, float) and math.isnan(growth_fraction)):
        return f'<p class="kpi-delta kpi-delta-neutral">N/A {comparison_note}</p>'
    is_good = growth_fraction >= 0 if positive_is_good else growth_fraction <= 0
    arrow = "▲" if growth_fraction >= 0 else "▼"
    css_class = "kpi-delta-positive" if is_good else "kpi-delta-negative"
    return (
        f'<p class="kpi-delta {css_class}">{arrow} {format_percent(growth_fraction, decimals)} '
        f"{comparison_note}</p>"
    )


def render_trend_card(container, label, value_text, growth_fraction, decimals=2, positive_is_good=True):
    """Render a KPI card: label, big value, and a colored trend delta.

    ``growth_fraction`` is a fraction (e.g. 0.0246 for +2.46%); pass ``None``
    when there is no valid comparison (e.g. the comparison period has zero
    orders). Set ``positive_is_good=False`` for metrics where a decrease is
    the desirable direction (e.g. delivery time), so the arrow still points
    in the direction of change but the color reflects whether that change is
    favorable.
    """
    html = (
        '<div class="kpi-card">'
        f'<p class="kpi-label">{label}</p>'
        f'<p class="kpi-value">{value_text}</p>'
        f"{_delta_html(growth_fraction, decimals, positive_is_good)}"
        "</div>"
    )
    container.markdown(html, unsafe_allow_html=True)


def render_growth_card(container, label, growth_fraction, decimals=2, note="Average across selected period"):
    """Render a KPI card whose value itself is a growth rate (colored by sign)."""
    if growth_fraction is None or (isinstance(growth_fraction, float) and math.isnan(growth_fraction)):
        value_text, value_class = "N/A", ""
    else:
        value_text = format_percent(growth_fraction, decimals)
        value_class = "kpi-value-positive" if growth_fraction >= 0 else "kpi-value-negative"

    html = (
        '<div class="kpi-card">'
        f'<p class="kpi-label">{label}</p>'
        f'<p class="kpi-value {value_class}">{value_text}</p>'
        f'<p class="kpi-delta kpi-delta-neutral">{note}</p>'
        "</div>"
    )
    container.markdown(html, unsafe_allow_html=True)


def render_review_card(container, score, subtitle="Average Review Score", max_score=5):
    """Render the review-score card: large number, star rating, subtitle."""
    if score is None or (isinstance(score, float) and math.isnan(score)):
        stars = "☆" * max_score
        value_text = "N/A"
    else:
        full_stars = int(round(score))
        stars = "★" * full_stars + "☆" * (max_score - full_stars)
        value_text = f"{score:.2f} / {max_score}"

    html = (
        '<div class="kpi-card">'
        f'<p class="kpi-value kpi-value-large">{value_text}</p>'
        f'<p class="kpi-stars">{stars}</p>'
        f'<p class="kpi-subtitle">{subtitle}</p>'
        "</div>"
    )
    container.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def build_revenue_trend_chart(current_series, previous_series, current_label, previous_label):
    """Line chart: solid line for the current period, dashed for the previous.

    Parameters
    ----------
    current_series, previous_series : pandas.Series
        Output of ``business_metrics.monthly_revenue_series``, indexed by
        monthly ``pandas.Period``. The two series are aligned by position
        (first month of the period against first month of the prior period,
        and so on) since their calendar months generally differ.
    current_label, previous_label : str
        Legend names, typically the formatted date ranges.
    """
    current_x = list(range(1, len(current_series) + 1))
    previous_x = list(range(1, len(previous_series) + 1))
    tick_labels = [period.strftime("%b %Y") for period in current_series.index]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=current_x,
        y=current_series.values,
        mode="lines+markers",
        name=current_label,
        line=dict(color=BLUE, width=3),
        marker=dict(size=7, color=BLUE),
        text=[p.strftime("%b %Y") for p in current_series.index],
        hovertemplate="%{text}<br>Revenue: %{customdata}<extra></extra>",
        customdata=[format_currency_full(v) for v in current_series.values],
    ))
    fig.add_trace(go.Scatter(
        x=previous_x,
        y=previous_series.values,
        mode="lines+markers",
        name=previous_label,
        line=dict(color=BLUE, width=2, dash="dash"),
        marker=dict(size=6, symbol="circle-open", color=BLUE),
        text=[p.strftime("%b %Y") for p in previous_series.index],
        hovertemplate="%{text}<br>Revenue: %{customdata}<extra></extra>",
        customdata=[format_currency_full(v) for v in previous_series.values],
    ))

    all_values = list(current_series.values) + list(previous_series.values)
    max_value = max(all_values) if all_values else 0
    ticks = nice_ticks(max_value)

    fig.update_layout(
        title="Revenue Trend",
        xaxis=dict(
            tickmode="array", tickvals=current_x, ticktext=tick_labels,
            title="Month", showgrid=True, gridcolor=GRID_COLOR,
        ),
        yaxis=dict(
            tickmode="array", tickvals=ticks,
            ticktext=[format_currency_short(t) for t in ticks],
            title="Revenue", showgrid=True, gridcolor=GRID_COLOR, rangemode="tozero",
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        height=CHART_HEIGHT,
        margin=dict(l=10, r=10, t=70, b=10),
        font=dict(color=INK),
    )
    return fig


def build_category_bar_chart(category_revenue, top_n=10):
    """Horizontal bar chart of the top ``top_n`` categories, blue gradient by value."""
    top = category_revenue.sort_values(ascending=False).head(top_n).sort_values(ascending=True)
    labels = [name.replace("_", " ").title() for name in top.index]

    fig = go.Figure(go.Bar(
        x=top.values,
        y=labels,
        orientation="h",
        marker=dict(color=top.values, colorscale=BLUE_SEQUENTIAL, showscale=False),
        text=[format_currency_short(v) for v in top.values],
        textposition="outside",
        hovertemplate="%{y}<br>Revenue: %{customdata}<extra></extra>",
        customdata=[format_currency_full(v) for v in top.values],
    ))

    ticks = nice_ticks(top.values.max() if len(top) else 0)
    fig.update_layout(
        title="Top 10 Product Categories by Revenue",
        xaxis=dict(
            tickmode="array", tickvals=ticks,
            ticktext=[format_currency_short(t) for t in ticks],
            title="Revenue", showgrid=True, gridcolor=GRID_COLOR,
        ),
        yaxis=dict(title=""),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=CHART_HEIGHT,
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(color=INK),
        showlegend=False,
    )
    return fig


def build_state_choropleth(state_revenue):
    """US choropleth of revenue by state, blue gradient by revenue amount."""
    fig = px.choropleth(
        state_revenue,
        locations="customer_state",
        color="price",
        locationmode="USA-states",
        scope="usa",
        color_continuous_scale=BLUE_SEQUENTIAL,
        labels={"price": "Revenue", "customer_state": "State"},
    )
    fig.update_traces(
        hovertemplate="%{location}<br>Revenue: $%{z:,.0f}<extra></extra>",
        marker_line_color="white",
        marker_line_width=0.5,
    )
    fig.update_layout(
        title="Revenue by State",
        coloraxis_colorbar=dict(title="Revenue", tickprefix="$"),
        height=CHART_HEIGHT,
        margin=dict(l=10, r=10, t=60, b=10),
        geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK),
    )
    return fig


def build_satisfaction_chart(review_by_tier):
    """Bar chart of average review score per delivery-speed tier."""
    fig = go.Figure(go.Bar(
        x=review_by_tier["delivery_tier"],
        y=review_by_tier["review_score"],
        marker=dict(color=BLUE),
        text=[f"{v:.2f}" for v in review_by_tier["review_score"]],
        textposition="outside",
        hovertemplate="%{x}<br>Avg review score: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="Average Review Score by Delivery Time",
        xaxis=dict(title="Delivery Time"),
        yaxis=dict(
            title="Average Review Score (1-5)", range=[0, 5.3],
            showgrid=True, gridcolor=GRID_COLOR,
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=CHART_HEIGHT,
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(color=INK),
        showlegend=False,
    )
    return fig
