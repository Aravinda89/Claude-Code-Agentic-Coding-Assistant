# E-Commerce Sales Analysis

Exploratory analysis of e-commerce order, product, customer, and review data:
revenue trends, product category and geographic breakdowns, and delivery
speed versus customer review scores.

## Project structure

```
Data_Analysis/
  ecommerce_data/            raw CSV source files
  data_loader.py             loading, cleaning, and period-filtering functions
  business_metrics.py        revenue / product / geographic / customer-experience metric functions
  dashboard_components.py    formatting, KPI cards, and Plotly chart builders for the dashboard
  app.py                     Streamlit dashboard
  EDA_Refactored.ipynb       the analysis notebook
  EDA.ipynb                  original, unrefactored notebook (kept for reference)
  requirements.txt           Python dependencies
```

`data_loader.py` and `business_metrics.py` contain no notebook- or
dashboard-specific code and no hard-coded dates -- they're imported by both
`EDA_Refactored.ipynb` and `app.py`, and can be reused from any other script.

## Setup

```
pip install -r requirements.txt
```

If you already have a Jupyter interface installed (JupyterLab, classic
Notebook, or the VS Code / PyCharm Jupyter extension), you only need the
first block of `requirements.txt` (pandas, numpy, matplotlib, plotly,
ipykernel).

## Running the analysis

Open `EDA_Refactored.ipynb` in Jupyter or your editor's notebook interface
and run all cells top to bottom. The notebook must be run with its working
directory set to `Data_Analysis/` (the same folder as `data_loader.py`,
`business_metrics.py`, and `ecommerce_data/`), which is the default when you
open the notebook directly from this folder.

## Configuring the analysis

Section 3 of the notebook ("Data Loading and Configuration") is the single
place that controls what gets analyzed:

```python
DATA_DIR = "ecommerce_data"

ANALYSIS_YEAR = 2023
ANALYSIS_MONTH = None      # 1-12 to scope to a single month; None = full year

COMPARISON_YEAR = 2022
COMPARISON_MONTH = None

DELIVERY_SPEED_BINS = [3, 7]
DELIVERY_SPEED_LABELS = ["1-3 days", "4-7 days", "8+ days"]
```

To analyze a different period, change `ANALYSIS_YEAR` / `ANALYSIS_MONTH` and
`COMPARISON_YEAR` / `COMPARISON_MONTH` and re-run the notebook -- no other
cell needs to change. For example, to analyze March 2023 against March 2022:

```python
ANALYSIS_YEAR = 2023
ANALYSIS_MONTH = 3
COMPARISON_YEAR = 2022
COMPARISON_MONTH = 3
```

`DELIVERY_SPEED_BINS` / `DELIVERY_SPEED_LABELS` control the delivery-speed
tiers used in the customer-experience charts. `DELIVERY_SPEED_BINS[i]` is the
inclusive upper bound, in days, of `DELIVERY_SPEED_LABELS[i]`; the last label
catches everything above the last bin. The two lists must stay the same
length (`len(labels) == len(bins) + 1`).

## Running the dashboard

```
streamlit run app.py
```

This opens the dashboard in your browser (default `http://localhost:8501`).
The Year and Month dropdowns in the top-right corner filter every card and
chart on the page at once. Year defaults to 2023; Month defaults to "All
Months" (the full year). Picking a specific month scopes every metric and
chart to that month only.

- **KPI row**: Total Revenue, Monthly Growth, Average Order Value, and Total
  Orders for the selected year/month. Total Revenue, Average Order Value,
  and Total Orders show a trend arrow and percentage versus the same period
  one year earlier (e.g. March 2023 is compared against March 2022; "All
  Months" for 2023 is compared against all of 2022). Monthly Growth is the
  average month-over-month revenue growth within the selected period itself
  (only meaningful when "All Months" is selected), and has no separate
  comparison.
- **Charts grid**: revenue trend (solid line for the selected period, dashed
  line for the comparison period), top 10 product categories by revenue,
  revenue by state, and average review score by delivery-speed tier.
- **Bottom row**: average delivery time (with a trend arrow -- colored
  green when delivery got *faster*, red when it got *slower*, since a lower
  number is the desirable direction) and the average review score with a
  star rating.

If the selected year/month has no delivered orders, the dashboard shows a
message instead of empty charts. If the comparison period (one year
earlier) has no delivered orders, trend indicators show "N/A" rather than a
divide-by-zero result.

To change the delivery-speed tiers used in the satisfaction chart, edit
`DELIVERY_SPEED_BINS` / `DELIVERY_SPEED_LABELS` at the top of `app.py` (same
convention as the notebook's Section 3 configuration).

## Reusing the modules

`data_loader.py` and `business_metrics.py` can be used outside the notebook,
for example against a future export of the same dataset shape:

```python
import data_loader as dl
import business_metrics as bm

datasets = dl.load_datasets("ecommerce_data")
orders = dl.prepare_orders(datasets["orders"])

sales = dl.build_sales_dataset(datasets["order_items"], orders)
sales_delivered = dl.filter_delivered(sales)
sales_q1_2024 = dl.filter_by_year_month(sales_delivered, year=2024, month=1)

print(bm.total_revenue(sales_q1_2024))
```

## Data dictionary

See Section 2 of `EDA_Refactored.ipynb` for the full column-level data
dictionary and business-term definitions (revenue, delivered order, average
order value, delivery speed).
