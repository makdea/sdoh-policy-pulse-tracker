"""
SDOH Policy Pulse Tracker — Plotly Dash dashboard.

Usage:
    python dashboard/app.py
    # Open http://127.0.0.1:8050 in your browser
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

GCP_PROJECT = os.environ["GCP_PROJECT"]
COUNTIES_GEOJSON = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)

_client = bigquery.Client(project=GCP_PROJECT)


def query(sql: str) -> pd.DataFrame:
    return _client.query(sql).to_dataframe()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_trends() -> pd.DataFrame:
    # Each row here is a single (county, year) observation, so a rate is
    # just numerator/denominator -- no cross-county weighting is involved
    # at this grain (that only matters once rows get aggregated, e.g. for
    # an era- or region-level rollup, which is now Lightdash's job).
    return query(f"""
        SELECT
            fct.county_fips, dim_county.county_name, dim_county.state_abbr,
            dim_county.state_name, dim_county.census_region,
            dim_county.is_expansion_state, dim_county.expansion_status,
            fct.year, dim_year.era_name, dim_year.era_color_hex,
            SAFE_DIVIDE(fct.n_uninsured, fct.sahie_total_population)        AS pct_uninsured,
            SAFE_DIVIDE(fct.unemployment_level, fct.labor_force_level)      AS unemployment_rate,
            SAFE_DIVIDE(fct.n_below_poverty, fct.poverty_universe)         AS poverty_rate,
            fct.median_household_income,
            SAFE_DIVIDE(fct.edu_bachelors, fct.edu_universe)               AS pct_bachelors_plus,
            SAFE_DIVIDE(fct.renters_severe_burden, fct.renters_total)      AS pct_severe_rent_burden,
            dim_year.policy_event_label
        FROM `{GCP_PROJECT}.dimensional.fct_county_year_sdoh` fct
        JOIN `{GCP_PROJECT}.dimensional.dim_county` dim_county ON fct.county_fips = dim_county.county_fips
        JOIN `{GCP_PROJECT}.dimensional.dim_year` dim_year ON fct.year = dim_year.year
        ORDER BY fct.county_fips, fct.year
    """)


trends_df = load_trends()

available_years = sorted(trends_df["year"].dropna().unique().tolist())

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METRIC_OPTIONS = [
    {"label": "% Uninsured",           "value": "pct_uninsured"},
    {"label": "Unemployment Rate (%)",  "value": "unemployment_rate"},
    {"label": "Poverty Rate (%)",       "value": "poverty_rate"},
    {"label": "Median HH Income ($)",   "value": "median_household_income"},
    {"label": "% Bachelor's+",          "value": "pct_bachelors_plus"},
    {"label": "% Severe Rent Burden",   "value": "pct_severe_rent_burden"},
]

METRIC_LABELS = {o["value"]: o["label"] for o in METRIC_OPTIONS}

PCT_METRICS = {"pct_uninsured", "unemployment_rate", "poverty_rate", "pct_bachelors_plus", "pct_severe_rent_burden"}

ERA_ORDER    = ["Trump1", "Biden", "Trump2"]
ERA_COLORS   = {"Trump1": "#e31a1c", "Biden": "#1f78b4", "Trump2": "#fc8d59"}
EXP_COLORS   = {"expanded": "#2166ac", "not_expanded": "#d6604d"}

ERA_SPANS = [("Trump1", 2017, 2020), ("Biden", 2021, 2024), ("Trump2", 2025, 2027)]


def to_pct(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    if col in PCT_METRICS:
        df[col] = df[col] * 100
    return df


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="SDOH Policy Pulse Tracker",
)

HEADER = dbc.Row(
    dbc.Col(
        html.Div([
            html.H2("SDOH Policy Pulse Tracker", className="mb-0"),
            html.P(
                "County-level social determinants of health across three political eras  "
                "· Trump 1 (2017–2020) · Biden (2021–2024) · Trump 2 (2025–)",
                className="text-muted",
            ),
        ]),
        className="py-3",
    )
)

# ── Tab 1 layout ────────────────────────────────────────────────────────────

TAB1 = dbc.Container(
    fluid=True,
    children=[
        # Controls row
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Outcome (Y-axis)", className="fw-semibold"),
                        dcc.Dropdown(
                            id="ts-metric",
                            options=METRIC_OPTIONS,
                            value="pct_uninsured",
                            clearable=False,
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.Label("Group lines by", className="fw-semibold"),
                        dcc.Dropdown(
                            id="ts-groupby",
                            options=[
                                {"label": "Era",                      "value": "era"},
                                {"label": "Expansion Status",         "value": "expansion"},
                                {"label": "Era × Expansion Status",   "value": "both"},
                            ],
                            value="era",
                            clearable=False,
                        ),
                    ],
                    md=4,
                ),
            ],
            className="mb-3 mt-2",
        ),

        # Time-series chart
        dbc.Card(
            [
                dbc.CardHeader("National Average Over Time"),
                dbc.CardBody(dcc.Graph(id="ts-chart", style={"height": "420px"})),
            ],
            className="mb-4",
        ),

        # Choropleth controls
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Year (map)", className="fw-semibold"),
                        dcc.Slider(
                            id="map-year",
                            min=min(available_years),
                            max=max(available_years),
                            step=1,
                            value=2020,
                            marks={y: str(y) for y in available_years},
                            tooltip={"placement": "bottom"},
                        ),
                    ],
                    md=10,
                ),
            ],
            className="mb-3",
        ),

        # Choropleth map
        dbc.Card(
            [
                dbc.CardHeader("County Map"),
                dbc.CardBody(dcc.Graph(id="choropleth", style={"height": "520px"})),
            ],
        ),
    ],
    className="pt-3",
)

# ── Tab placeholders ─────────────────────────────────────────────────────────

def placeholder_tab(label: str) -> dbc.Container:
    return dbc.Container(
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.H4(label, className="text-muted mt-5"),
                        html.P("Content coming soon.", className="text-muted"),
                    ],
                    className="text-center py-5",
                )
            )
        ),
        className="pt-4",
    )


# ── Full layout ───────────────────────────────────────────────────────────────

app.layout = dbc.Container(
    fluid=True,
    children=[
        HEADER,
        dbc.Tabs(
            [
                dbc.Tab(TAB1,                          label="Trends",              tab_id="tab-trends"),
                dbc.Tab(placeholder_tab("Era Analysis"), label="Era Analysis",      tab_id="tab-era"),
                dbc.Tab(placeholder_tab("Diff-in-Diff"),  label="Diff-in-Diff",    tab_id="tab-did"),
                dbc.Tab(placeholder_tab("County Drill-Down"), label="County Drill-Down", tab_id="tab-county"),
            ],
            id="main-tabs",
            active_tab="tab-trends",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("ts-chart", "figure"),
    Input("ts-metric", "value"),
    Input("ts-groupby", "value"),
)
def update_timeseries(metric: str, groupby: str) -> go.Figure:
    label = METRIC_LABELS.get(metric, metric)

    if groupby == "era":
        df = (
            trends_df.groupby(["year", "era_name"])[metric]
            .mean()
            .reset_index()
        )
        df = to_pct(df, metric)
        fig = px.line(
            df,
            x="year", y=metric,
            color="era_name",
            color_discrete_map=ERA_COLORS,
            markers=True,
            labels={metric: label, "year": "Year", "era_name": "Era"},
            category_orders={"era_name": ERA_ORDER},
        )

    elif groupby == "expansion":
        df = (
            trends_df.groupby(["year", "expansion_status"])[metric]
            .mean()
            .reset_index()
        )
        df = to_pct(df, metric)
        fig = px.line(
            df,
            x="year", y=metric,
            color="expansion_status",
            color_discrete_map=EXP_COLORS,
            markers=True,
            labels={metric: label, "year": "Year", "expansion_status": "Medicaid Status"},
        )

    else:  # both
        df = (
            trends_df.groupby(["year", "era_name", "expansion_status"])[metric]
            .mean()
            .reset_index()
        )
        df = to_pct(df, metric)
        df["group"] = df["era_name"] + " / " + df["expansion_status"]
        fig = px.line(
            df,
            x="year", y=metric,
            color="era_name",
            line_dash="expansion_status",
            markers=True,
            labels={metric: label, "year": "Year", "era_name": "Era", "expansion_status": "Medicaid Status"},
            category_orders={"era_name": ERA_ORDER},
            color_discrete_map=ERA_COLORS,
        )

    # Shade era bands
    for era, start, end in ERA_SPANS:
        fig.add_vrect(
            x0=start - 0.5, x1=end + 0.5,
            fillcolor=ERA_COLORS[era],
            opacity=0.06,
            layer="below",
            line_width=0,
            annotation_text=era,
            annotation_position="top left",
            annotation_font_size=10,
            annotation_font_color=ERA_COLORS[era],
        )

    fig.update_layout(
        margin={"t": 30, "b": 40},
        legend={"title": None},
        hovermode="x unified",
    )
    return fig


@app.callback(
    Output("choropleth", "figure"),
    Input("map-year", "value"),
    Input("ts-metric", "value"),
)
def update_choropleth(year: int, metric: str) -> go.Figure:
    df = trends_df[trends_df["year"] == year].copy()
    label = METRIC_LABELS.get(metric, metric)

    display_col = metric
    if metric in PCT_METRICS:
        df["_display"] = df[metric] * 100
        display_col = "_display"

    era_label = next((e for e, s, en in ERA_SPANS if s <= year <= en), "")

    fig = px.choropleth(
        df.dropna(subset=[display_col]),
        geojson=COUNTIES_GEOJSON,
        locations="county_fips",
        color=display_col,
        color_continuous_scale="RdYlGn_r",
        scope="usa",
        hover_name="county_name",
        hover_data={"state_abbr": True, "county_fips": False},
        labels={display_col: label},
        title=f"{label} · {year}  [{era_label or 'pre-era'}]",
    )
    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        coloraxis_colorbar={"thickness": 12},
    )
    return fig


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=8050)
