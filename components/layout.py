"""
components/layout.py
Builds the dashboard layout.
Each section is a reusable function independent of data state.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc

COLORS = {
    "danger":  "#E24B4A",
    "warning": "#EF9F27",
    "info":    "#378ADD",
    "success": "#639922",
}


# ── Componentes atômicos ────────────────────────────────────────────────────────

def kpi_card(card_id: str, label: str, default: str, sub: str, accent: str) -> dbc.Col:
    """Reusable executive metric card."""
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.P(label, className="kpi-label text-muted small mb-1"),
                html.H3(default, id=card_id,
                        style={"color": COLORS[accent], "fontWeight": 500}),
                html.Small(sub, className="text-muted"),
            ]),
            className="h-100 border",
        ),
        xs=12, sm=6, md=3,
    )


def filter_bar() -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Product Type", className="small text-muted"),
                    dcc.Dropdown(
                        id="filter-type",
                        options=[
                            {"label": "All",    "value": "ALL"},
                            {"label": "Type L", "value": "L"},
                            {"label": "Type M", "value": "M"},
                            {"label": "Type H", "value": "H"},
                        ],
                        value="ALL",
                        clearable=False,
                    ),
                ], md=3),

                dbc.Col([
                    html.Label("Tool Wear (min)", className="small text-muted"),
                    dcc.RangeSlider(
                        id="filter-wear",
                        min=0, max=250, step=10,
                        value=[0, 250],
                        marks={0: "0", 100: "100", 200: "200", 250: "250"},
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ], md=5),

                dbc.Col([
                    html.Label("Show", className="small text-muted"),
                    dbc.RadioItems(
                        id="filter-status",
                        options=[
                            {"label": "All",        "value": "ALL"},
                            {"label": "Failures",   "value": "FAIL"},
                            {"label": "Operational","value": "OK"},
                        ],
                        value="ALL",
                        inline=True,
                        className="mt-1",
                    ),
                ], md=4),
            ], align="center"),
        ),
        className="mb-3",
    )


def kpi_row() -> dbc.Row:
    return dbc.Row([
        kpi_card("kpi-fail-rate",  "Failure Rate",            "—%",    "of all equipment",         "danger"),
        kpi_card("kpi-wear",       "Avg Wear at Failure",     "— min", "estimated critical limit", "warning"),
        kpi_card("kpi-main-mode",  "Main Failure Mode",       "—",     "most frequent type",       "info"),
        kpi_card("kpi-risk",       "Avg Risk Score",          "—",     "current fleet",            "success"),
    ], className="g-3 mb-3")


def main_charts_row() -> dbc.Row:
    return dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    "Scatter: Torque × Speed  (click for details)",
                    html.Button(
                        html.I(className="fa-solid fa-expand"),
                        id="btn-fullscreen-scatter",
                        className="btn btn-sm btn-outline-secondary ms-2",
                        title="Toggle Fullscreen",
                    ),
                ], className="d-flex justify-content-between align-items-center"),
                dbc.CardBody(dcc.Graph(
                    id="chart-scatter",
                    config={"displayModeBar": False},
                    style={"height": "320px"},
                )),
            ]),
            md=8,
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    "Failure Modes Distribution",
                    html.Button(
                        html.I(className="fa-solid fa-expand"),
                        id="btn-fullscreen-failure-modes",
                        className="btn btn-sm btn-outline-secondary ms-2",
                        title="Toggle Fullscreen",
                    ),
                ], className="d-flex justify-content-between align-items-center"),
                dbc.CardBody(dcc.Graph(
                    id="chart-failure-modes",
                    config={"displayModeBar": False},
                    style={"height": "320px"},
                )),
            ]),
            md=4,
        ),
    ], className="g-3 mb-3")


def bottom_row() -> dbc.Row:
    return dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    "Sensors by Status",
                    html.Button(
                        html.I(className="fa-solid fa-expand"),
                        id="btn-fullscreen-sensors",
                        className="btn btn-sm btn-outline-secondary ms-2",
                        title="Toggle Fullscreen",
                    ),
                ], className="d-flex justify-content-between align-items-center"),
                dbc.CardBody(dcc.Graph(
                    id="chart-sensors",
                    config={"displayModeBar": False},
                    style={"height": "280px"},
                )),
            ]),
            md=4,
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    "Failure Rate by Product Type",
                    html.Button(
                        html.I(className="fa-solid fa-expand"),
                        id="btn-fullscreen-chart-by-type",
                        className="btn btn-sm btn-outline-secondary ms-2",
                        title="Toggle Fullscreen",
                    ),
                ], className="d-flex justify-content-between align-items-center"),
                dbc.CardBody(dcc.Graph(
                    id="chart-by-type",
                    config={"displayModeBar": False},
                    style={"height": "280px"},
                )),
            ]),
            md=4,
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    "Recent Alerts  ",
                    dbc.Badge("0", id="badge-alerts", color="danger", pill=True),
                ]),
                dbc.CardBody(
                    html.Div(
                        id="alerts-list",
                        style={"maxHeight": "280px", "overflowY": "auto"},
                    ),
                ),
            ]),
            md=4,
        ),
    ], className="g-3 mb-3")


def detail_modal() -> dbc.Modal:
    """Drill-down modal opened when clicking on scatter."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),
        dbc.ModalBody(
            dbc.Row([
                dbc.Col(dcc.Graph(id="modal-radar",   config={"displayModeBar": False}), md=6),
                dbc.Col(dcc.Graph(id="modal-history", config={"displayModeBar": False}), md=6),
            ])
        ),
        dbc.ModalFooter(
            dbc.Button("Close", id="modal-close", color="secondary", outline=True, size="sm")
        ),
    ], id="detail-modal", size="xl", is_open=False)


# ── Stores e controles de estado ────────────────────────────────────────────────
def data_stores() -> list:
    return [
        dcc.Store(id="store-data",           storage_type="memory"),
        dcc.Store(id="store-filtered",       storage_type="memory"),
        dcc.Store(id="store-selected-uid",   storage_type="memory"),
        # Intervalo para simular refresh periódico (60s)
        dcc.Interval(id="interval-refresh",  interval=60_000, n_intervals=0),
        # Hidden div to capture keyboard events (will be handled clientside)
        html.Div(id="keyboard-listener", 
                 style={"position": "fixed", "top": 0, "left": 0, "width": "1px", "height": "1px", "overflow": "hidden"},
                 tabIndex=0),
    ]


# ── Layout principal ────────────────────────────────────────────────────────────
def build_layout() -> html.Div:
    return html.Div([
        *data_stores(),

        dbc.Navbar(
            dbc.Container([
                html.Span("Predictive Maintenance Dashboard",
                          className="navbar-brand fw-bold"),
                html.Small("AI4I 2020", className="text-muted ms-2 d-none d-md-inline"),
                dbc.NavItem(
                    dbc.Badge(
                        "Loading…",
                        id="data-status",
                        color="warning",
                        pill=True,
                        className="ms-auto",
                    ),
                ),
            ], fluid=True),
            color="white", dark=False, className="border-bottom mb-3 shadow-sm",
        ),

        dbc.Container([
            filter_bar(),
            kpi_row(),
            main_charts_row(),
            bottom_row(),
            detail_modal(),
        ], fluid=True),

        # Fullscreen Modals
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="fullscreen-scatter-title")),
            dbc.ModalBody(dcc.Graph(
                id="fullscreen-scatter-graph",
                config={"displayModeBar": True, "responsive": True},
                style={"height": "80vh"}
            )),
            dbc.ModalFooter(
                dbc.Button("Close", id="btn-close-fullscreen-scatter", className="ms-auto")
            ),
        ], id="fullscreen-scatter-modal", size="xl", is_open=False),

        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="fullscreen-failure-modes-title")),
            dbc.ModalBody(dcc.Graph(
                id="fullscreen-failure-modes-graph",
                config={"displayModeBar": True, "responsive": True},
                style={"height": "80vh"}
            )),
            dbc.ModalFooter(
                dbc.Button("Close", id="btn-close-fullscreen-failure-modes", className="ms-auto")
            ),
        ], id="fullscreen-failure-modes-modal", size="xl", is_open=False),

        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="fullscreen-sensors-title")),
            dbc.ModalBody(dcc.Graph(
                id="fullscreen-sensors-graph",
                config={"displayModeBar": True, "responsive": True},
                style={"height": "80vh"}
            )),
            dbc.ModalFooter(
                dbc.Button("Close", id="btn-close-fullscreen-sensors", className="ms-auto")
            ),
        ], id="fullscreen-sensors-modal", size="xl", is_open=False),

        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="fullscreen-chart-by-type-title")),
            dbc.ModalBody(dcc.Graph(
                id="fullscreen-chart-by-type-graph",
                config={"displayModeBar": True, "responsive": True},
                style={"height": "80vh"}
            )),
            dbc.ModalFooter(
                dbc.Button("Close", id="btn-close-fullscreen-chart-by-type", className="ms-auto")
            ),
        ], id="fullscreen-chart-by-type-modal", size="xl", is_open=False),

        # Dummy output for clientside callback
        html.Div(id="dummy-output", style={"display": "none"}),
    ])
