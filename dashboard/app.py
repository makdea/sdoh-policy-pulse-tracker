"""
SDOH Policy Pulse Tracker — Plotly Dash dashboard.

Panels:
  1. Choropleth map  — county uninsured rate, slideable by year
  2. Era comparison  — avg outcomes by era × expansion status (bar chart)
  3. DiD plot        — treatment vs control trend lines with era shading
  4. County drill-down — click a county, get its full SDOH time series
  5. Correlation scatter — unemployment vs uninsured, colored by era

Usage:
    python dashboard/app.py
    # Open http://127.0.0.1:8050 in your browser
"""

import os
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, callback_context

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

DB_PATH = os.environ.get("DUCKDB_PATH", "data/sdoh_pulse.duckdb")
COUNTIES_GEOJSON = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)


def query(sql: str) -> pd.DataFrame:
    conn = duckdb.connect(DB_PATH, read_only=True)
    df = conn.execute(sql).df()
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_trends() -> pd.DataFrame:
    return query("""
        SELECT
            county_fips, county_name, state_abbr, state_name,
            census_region, is_expansion_state, expansion_status,
            year, era_name, era_color_hex,
            pct_uninsured, unemployment_rate, poverty_rate,
            median_household_income, pct_bachelors_plus,
            pct_severe_rent_burden, policy_event_label
        FROM marts.mart_county_sdoh_trends
        ORDER BY county_fips, year
    """)


def load_era_comparisons() -> pd.DataFrame:
    return query("""
        SELECT *
        FROM marts.mart_era_comparisons
        WHERE census_region IS NOT NULL
        ORDER BY era_sort_order, is_expansion_state DESC
    """)


def load_did() -> pd.DataFrame:
    return query("SELECT * FROM marts.mart_diff_in_diff")


trends_df = load_trends()
era_df = load_era_comparisons()
did_df = load_did()

available_years = sorted(trends_df["year"].dropna().unique().tolist())
era_colors = {"Trump1": "#e31a1c", "Biden": "#1f78b4", "Trump2": "#fc8d59"}

# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="SDOH Policy Pulse Tracker",
)

SIDEBAR = dbc.Card(
    [
        html.H5("Filters", className="card-title"),
        html.Hr(),
        html.Label("Year (choropleth)"),
        dcc.Slider(
            id="year-slider",
            min=min(available_years),
            max=max(available_years),
            step=1,
            value=2020,
            marks={y: str(y) for y in available_years},
        ),
        html.Br(),
        html.Label("Outcome metric"),
        dcc.Dropdown(
            id="metric-dropdown",
            options=[
                {"label": "% Uninsured",            "value": "pct_uninsured"},
                {"label": "Unemployment Rate (%)",   "value": "unemployment_rate"},
                {"label": "Poverty Rate",            "value": "poverty_rate"},
                {"label": "Median HH Income ($)",    "value": "median_household_income"},
                {"label": "% Bachelor's+",           "value": "pct_bachelors_plus"},
                {"label": "% Severe Rent Burden",    "value": "pct_severe_rent_burden"},
            ],
            value="pct_uninsured",
            clearable=False,
        ),
        html.Br(),
        html.Label("Era comparison metric"),
        dcc.Dropdown(
            id="era-metric-dropdown",
            options=[
                {"label": "% Uninsured",          "value": "avg_pct_uninsured"},
                {"label": "Unemployment Rate",    "value": "avg_unemployment_rate"},
                {"label": "Poverty Rate",         "value": "avg_poverty_rate"},
                {"label": "Median HH Income",     "value": "avg_median_hh_income"},
            ],
            value="avg_pct_uninsured",
            clearable=False,
        ),
    ],
    body=True,
    className="mb-3",
)

app.layout = dbc.Container(
    fluid=True,
    children=[
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.H2("SDOH Policy Pulse Tracker", className="mb-0"),
                        html.P(
                            "County-level social determinants of health across three political eras  "
                            "· Trump 1 (2017–2020) · Biden (2021–2024) · Trump 2 (2025–)",
                            className="text-muted",
                        ),
                    ]
                ),
                className="py-3",
            )
        ),
        dbc.Row(
            [
                dbc.Col(SIDEBAR, md=2),
                dbc.Col(
                    [
                        # ── Panel 1: Choropleth ──────────────────────────
                        dbc.Card(
                            [
                                dbc.CardHeader("County Map"),
                                dbc.CardBody(
                                    dcc.Graph(id="choropleth", style={"height": "420px"})
                                ),
                            ],
                            className="mb-3",
                        ),

                        dbc.Row(
                            [
                                # ── Panel 2: Era comparison bars ──────────
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Era Comparison by Expansion Status"),
                                            dbc.CardBody(
                                                dcc.Graph(id="era-bar", style={"height": "320px"})
                                            ),
                                        ]
                                    ),
                                    md=6,
                                ),

                                # ── Panel 3: DiD plot ────────────────────
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Difference-in-Differences (Trump1 → Biden)"),
                                            dbc.CardBody(
                                                dcc.Graph(id="did-chart", style={"height": "320px"})
                                            ),
                                        ]
                                    ),
                                    md=6,
                                ),
                            ],
                            className="mb-3",
                        ),

                        dbc.Row(
                            [
                                # ── Panel 4: County drill-down ───────────
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                "County Drill-Down  (click map county)"
                                            ),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        id="drilldown-title",
                                                        className="text-muted mb-2",
                                                    ),
                                                    dcc.Graph(
                                                        id="drilldown-chart",
                                                        style={"height": "280px"},
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                    md=6,
                                ),

                                # ── Panel 5: Correlation scatter ─────────
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                "Unemployment vs Uninsured Rate (by era)"
                                            ),
                                            dbc.CardBody(
                                                dcc.Graph(
                                                    id="scatter-chart",
                                                    style={"height": "280px"},
                                                )
                                            ),
                                        ]
                                    ),
                                    md=6,
                                ),
                            ]
                        ),
                    ],
                    md=10,
                ),
            ]
        ),
    ],
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

METRIC_LABELS = {
    "pct_uninsured":          "% Uninsured",
    "unemployment_rate":      "Unemployment Rate (%)",
    "poverty_rate":           "Poverty Rate",
    "median_household_income":"Median HH Income ($)",
    "pct_bachelors_plus":     "% Bachelor's+",
    "pct_severe_rent_burden": "% Severe Rent Burden",
}


@app.callback(
    Output("choropleth", "figure"),
    Input("year-slider", "value"),
    Input("metric-dropdown", "value"),
)
def update_choropleth(year, metric):
    df = trends_df[trends_df["year"] == year].copy()
    label = METRIC_LABELS.get(metric, metric)

    display_col = metric
    if metric == "pct_uninsured":
        df["display"] = df[metric] * 100
        display_col = "display"
        label = "% Uninsured"
    elif metric == "poverty_rate":
        df["display"] = df[metric] * 100
        display_col = "display"
        label = "Poverty Rate (%)"
    elif metric == "pct_bachelors_plus":
        df["display"] = df[metric] * 100
        display_col = "display"
        label = "% Bachelor's+"
    elif metric == "pct_severe_rent_burden":
        df["display"] = df[metric] * 100
        display_col = "display"
        label = "% Severe Rent Burden"

    # Detect which era this year falls in
    era_spans = [("Trump1", 2017, 2020), ("Biden", 2021, 2024), ("Trump2", 2025, 2027)]
    era_label = next((e for e, s, en in era_spans if s <= year <= en), "")

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


@app.callback(
    Output("era-bar", "figure"),
    Input("era-metric-dropdown", "value"),
)
def update_era_bar(metric):
    df = (
        era_df.groupby(["era_name", "expansion_status", "era_sort_order"])
        [metric]
        .mean()
        .reset_index()
        .sort_values("era_sort_order")
    )
    label_map = {
        "avg_pct_uninsured":    "Avg % Uninsured",
        "avg_unemployment_rate":"Avg Unemployment (%)",
        "avg_poverty_rate":     "Avg Poverty Rate",
        "avg_median_hh_income": "Avg Median HH Income ($)",
    }
    label = label_map.get(metric, metric)

    if metric == "avg_pct_uninsured":
        df[metric] = df[metric] * 100
    elif metric == "avg_poverty_rate":
        df[metric] = df[metric] * 100

    fig = px.bar(
        df,
        x="era_name",
        y=metric,
        color="expansion_status",
        barmode="group",
        color_discrete_map={
            "expanded":     "#2166ac",
            "not_expanded": "#d6604d",
        },
        labels={metric: label, "era_name": "Era", "expansion_status": "Medicaid Status"},
        category_orders={"era_name": ["Trump1", "Biden", "Trump2"]},
    )
    fig.update_layout(margin={"t": 20, "b": 40}, legend={"title": None})
    return fig


@app.callback(
    Output("did-chart", "figure"),
    Input("era-metric-dropdown", "value"),
)
def update_did_chart(_metric):
    outcome_map = {
        "avg_pct_uninsured":    "pct_uninsured",
        "avg_unemployment_rate":"unemployment_rate",
        "avg_poverty_rate":     "poverty_rate",
        "avg_median_hh_income": "median_household_income",
    }
    # Show all four DiD estimates as a waterfall / bar
    df = did_df.copy()
    df["did_pct"] = df["did_estimate_pct_pts"]
    df["color"] = df["did_pct"].apply(
        lambda v: "#2166ac" if v < 0 else "#d6604d"
    )

    fig = go.Figure()
    for _, row in df.iterrows():
        outcome_label = row["outcome"].replace("_", " ").title()
        fig.add_trace(
            go.Bar(
                name=outcome_label,
                x=[outcome_label],
                y=[row["did_pct"]],
                marker_color=row["color"],
                text=f"{row['did_pct']:+.2f}",
                textposition="outside",
                hovertemplate=(
                    f"<b>{outcome_label}</b><br>"
                    f"Treated change: {row['treated_change']:.4f}<br>"
                    f"Control change: {row['control_change']:.4f}<br>"
                    f"DiD estimate: {row['did_pct']:+.2f} pct pts<br>"
                    f"<i>{row['interpretation_note']}</i>"
                ),
                showlegend=False,
            )
        )

    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="DiD: Expansion − Non-expansion (Trump1→Biden)",
        yaxis_title="DiD estimate (pct pts)",
        xaxis_title=None,
        margin={"t": 50, "b": 40},
        annotations=[
            dict(
                text="Blue = expansion improved more  |  Red = expansion improved less",
                xref="paper", yref="paper",
                x=0, y=-0.18, showarrow=False,
                font=dict(size=10, color="gray"),
            )
        ],
    )
    return fig


@app.callback(
    Output("drilldown-chart", "figure"),
    Output("drilldown-title", "children"),
    Input("choropleth", "clickData"),
    Input("metric-dropdown", "value"),
)
def update_drilldown(click_data, metric):
    if click_data is None:
        fips = "06037"  # Default: Los Angeles County
        name = "Los Angeles County, CA"
    else:
        fips = click_data["points"][0]["location"]
        name = click_data["points"][0].get("hovertext", fips)

    df = trends_df[trends_df["county_fips"] == fips].sort_values("year")
    label = METRIC_LABELS.get(metric, metric)

    if metric in ("pct_uninsured", "poverty_rate", "pct_bachelors_plus", "pct_severe_rent_burden"):
        df = df.copy()
        df[metric] = df[metric] * 100

    fig = px.line(
        df,
        x="year",
        y=metric,
        markers=True,
        color="era_name",
        color_discrete_map=era_colors,
        labels={metric: label, "year": "Year", "era_name": "Era"},
    )

    # Annotate policy events
    for _, row in df[df["policy_event_label"].notna()].iterrows():
        fig.add_vline(
            x=row["year"],
            line_dash="dash",
            line_color="gray",
            annotation_text=row["policy_event_label"][:30],
            annotation_position="top left",
            annotation_font_size=9,
        )

    fig.update_layout(margin={"t": 20, "b": 30}, legend={"title": None})

    title_text = f"Selected county: {name} (FIPS {fips})"
    return fig, title_text


@app.callback(
    Output("scatter-chart", "figure"),
    Input("year-slider", "value"),
)
def update_scatter(year):
    df = trends_df[
        trends_df["year"] == year
    ].dropna(subset=["unemployment_rate", "pct_uninsured"]).copy()
    df["pct_uninsured_pct"] = df["pct_uninsured"] * 100

    era = df["era_name"].iloc[0] if len(df) else ""
    color = era_colors.get(era, "#888")

    fig = px.scatter(
        df,
        x="unemployment_rate",
        y="pct_uninsured_pct",
        color="is_expansion_state",
        color_discrete_map={True: "#2166ac", False: "#d6604d"},
        opacity=0.5,
        size_max=6,
        hover_name="county_name",
        hover_data={"state_abbr": True, "is_expansion_state": False},
        labels={
            "unemployment_rate":   "Unemployment Rate (%)",
            "pct_uninsured_pct":   "% Uninsured",
            "is_expansion_state":  "Medicaid Expanded",
        },
        trendline="ols",
        trendline_scope="overall",
        title=f"Unemployment vs Uninsured  ·  {year}  [{era}]",
    )
    fig.update_layout(margin={"t": 50, "b": 30}, legend={"title": "Medicaid Expanded"})
    return fig


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    app.run(debug=True, port=8050)
