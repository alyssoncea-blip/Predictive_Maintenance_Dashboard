"""
components/figures.py
Plotly visualization functions for the dashboard.
Each function returns a Plotly figure ready-to-render.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = {
    "danger":  "#E24B4A",
    "warning": "#EF9F27",
    "info":    "#378ADD",
    "success": "#639922",
    "blue_l": "#B5D4F4",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _get_layout(title: str, height: int = None) -> dict:
    """Layout base para todos os gráficos."""
    layout = {
        "title": {"text": title, "font": {"size": 12}},
        "margin": {"l": 40, "r": 20, "t": 40, "b": 30},
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
        "font": {"size": 10},
    }
    if height:
        layout["height"] = height
    return layout


# ─────────────────────────────────────────────────────────────────────────────
# Scatter: Torque x RPM
# ─────────────────────────────────────────────────────────────────────────────
def scatter_torque_rpm(df: pd.DataFrame) -> dict:
    """Scatter Torque x Speed with critical zones."""
    fig = go.Figure()

    # Normal (Machine failure = 0)
    normal = df[df["Machine failure"] == 0]
    fig.add_trace(go.Scatter(
        x=normal["Rotational speed [rpm]"],
        y=normal["Torque [Nm]"],
        mode="markers",
        marker=dict(
            size=5,
            color=COLORS["blue_l"],
            opacity=0.6,
        ),
        name="Normal",
        hovertemplate="RPM: %{x}<br>Torque: %{y}Nm<extra></extra>",
    ))

    # Failure (Machine failure = 1)
    failed = df[df["Machine failure"] == 1]
    if len(failed) > 0:
        fig.add_trace(go.Scatter(
            x=failed["Rotational speed [rpm]"],
            y=failed["Torque [Nm]"],
            mode="markers",
            marker=dict(
                size=7,
                color=COLORS["danger"],
                opacity=0.9,
                line=dict(width=1, color="white"),
            ),
            name="Failure",
            hovertemplate="RPM: %{x}<br>Torque: %{y}Nm<extra></extra>",
        ))

    # Critical zone: low RPM + high Torque
    fig.add_shape(
        type="rect",
        x0=0, y0=50,
        x1=1200, y1=100,
        fillcolor=COLORS["warning"],
        opacity=0.1,
        line=dict(color=COLORS["warning"], width=1, dash="dash"),
    )
    fig.add_annotation(x=600, y=75, text="Critical Zone", showarrow=False,
                      font=dict(size=9, color=COLORS["warning"]))

    # Critical zone: high RPM + high Torque
    fig.add_shape(
        type="rect",
        x0=1800, y0=50,
        x1=2500, y1=100,
        fillcolor=COLORS["danger"],
        opacity=0.1,
        line=dict(color=COLORS["danger"], width=1, dash="dash"),
    )
    fig.add_annotation(x=2150, y=75, text="Critical Zone", showarrow=False,
                      font=dict(size=9, color=COLORS["danger"]))

    fig.update_layout(
        **_get_layout("Torque × Speed of Rotation"),
        xaxis_title="Rotational speed (rpm)",
        yaxis_title="Torque (Nm)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest",
    )
    return fig.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# Bar: Failure Modes
# ─────────────────────────────────────────────────────────────────────────────
def bar_failure_modes(dist_df: pd.DataFrame) -> dict:
    """Barras horizontais para distribuição de modos de falha."""
    colors_map = {
        "HDF": COLORS["danger"],
        "PWF": COLORS["warning"],
        "OSF": "#BA7517",
        "TWF": COLORS["info"],
        "RNF": "#B4B2A9",
    }

    fig = go.Figure()
    for _, row in dist_df.iterrows():
        mode = row["mode"]
        fig.add_trace(go.Bar(
            x=[row["pct"]],
            y=[mode],
            orientation="h",
            marker_color=colors_map.get(mode, COLORS["info"]),
            name=mode,
            hovertemplate=f"{mode}: {row['pct']}%<br>Count: {row['count']}<extra></extra>",
            text=f"{row['pct']}%",
            textposition="auto",
        ))

    fig.update_layout(
        **_get_layout("Distribuição de Modos de Falha"),
        xaxis_title="% do total de falhas",
        yaxis_title="Modo",
        showlegend=False,
        bargap=0.3,
    )
    return fig.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# Boxplot: Sensores
# ─────────────────────────────────────────────────────────────────────────────
def boxplot_sensors(df: pd.DataFrame) -> dict:
    """Boxplot of sensors by failure status."""
    sensor_cols = [
        "Air temperature [K]",
        "Process temperature [K]",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]",
    ]

    fig = go.Figure()

    # Normal
    normal = df[df["Machine failure"] == 0]
    for col in sensor_cols:
        fig.add_trace(go.Box(
            y=normal[col],
            name=col.split(" [")[0],
            marker_color=COLORS["info"],
            boxmean="sd",
        ))

    # Failure (only if exists)
    failed = df[df["Machine failure"] == 1]
    if len(failed) > 0:
        for col in sensor_cols:
            fig.add_trace(go.Box(
                y=failed[col],
                name=col.split(" [")[0] + " (failure)",
                marker_color=COLORS["danger"],
                boxmean="sd",
            ))

    fig.update_layout(
        **_get_layout("Sensors by Status"),
        yaxis_title="Value",
        showlegend=False,
        boxmode="group",
    )
    return fig.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# Bar: Failure by Type
# ─────────────────────────────────────────────────────────────────────────────
def bar_by_type(type_df: pd.DataFrame) -> dict:
    """Bars for failure rate by product type."""
    colors_map = {"L": COLORS["danger"], "M": COLORS["warning"], "H": COLORS["success"]}

    fig = go.Figure()
    for _, row in type_df.iterrows():
        fig.add_trace(go.Bar(
            x=[row["Type"]],
            y=[row["fail_rate_pct"]],
            marker_color=colors_map.get(row["Type"], COLORS["info"]),
            name=row["Type"],
            hovertemplate=f"Type {row['Type']}: {row['fail_rate_pct']}%<extra></extra>",
            text=f"{row['fail_rate_pct']}%",
            textposition="auto",
        ))

    fig.update_layout(
        **_get_layout("Failure Rate by Product Type"),
        xaxis_title="Product type",
        yaxis_title="Failure rate (%)",
        showlegend=False,
    )
    return fig.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# Radar: Sensores (Modal drill-down)
# ─────────────────────────────────────────────────────────────────────────────
def radar_sensors(row: pd.Series, df: pd.DataFrame) -> dict:
    """Radar chart for equipment profile vs fleet average."""
    cols = [
        "Air temperature [K]",
        "Process temperature [K]",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]",
    ]
    labels = ["Air T", "Process T", "RPM", "Torque", "Tool Wear"]

    # Normalize to 0-100
    max_vals = {c: df[c].max() for c in cols}
    values = [(row[c] / max_vals[c]) * 100 if max_vals[c] > 0 else 0 for c in cols]

    # Fleet average
    fleet_avg = [(df[c].mean() / max_vals[c]) * 100 for c in cols]

    fig = go.Figure()

    # Equipment
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name="This equipment",
        line_color=COLORS["danger"],
        fillcolor=COLORS["danger"],
        opacity=0.4,
    ))

    # Fleet average
    fig.add_trace(go.Scatterpolar(
        r=fleet_avg + [fleet_avg[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name="Fleet average",
        line_color=COLORS["info"],
        fillcolor="transparent",
        line_dash="dash",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 100], showticklabels=True, ticks="")
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    )
    return fig.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# Line: Sensor History (Modal)
# ─────────────────────────────────────────────────────────────────────────────
def sensor_history(df: pd.DataFrame, uid: int) -> dict:
    """Time series of sensors for a specific UID."""
    # Sort by UDI
    df_sorted = df.sort_values("UDI")
    
    # Find UID index
    idx = df_sorted[df_sorted["UDI"] == uid].index
    if len(idx) == 0:
        idx = [0]
    
    pos = df_sorted.index.get_loc(idx[0])
    
    # Window of 20 records (10 before, 10 after)
    start = max(0, pos - 10)
    end = min(len(df_sorted), pos + 10)
    window = df_sorted.iloc[start:end]
    
    fig = go.Figure()
    
    # Tool wear
    fig.add_trace(go.Scatter(
        x=window["UDI"],
        y=window["Tool wear [min]"],
        mode="lines+markers",
        name="Tool wear",
        line=dict(color=COLORS["danger"], width=2),
        yaxis="y1",
    ))
    
    # Risk score
    fig.add_trace(go.Scatter(
        x=window["UDI"],
        y=window["Risk score"],
        mode="lines",
        name="Risk score",
        line=dict(color=COLORS["warning"], width=2, dash="dot"),
        yaxis="y2",
    ))
    
    # Mark current point
    current = window[window["UDI"] == uid]
    if not current.empty:
        fig.add_trace(go.Scatter(
            x=current["UDI"],
            y=current["Tool wear [min]"],
            mode="markers",
            marker=dict(size=12, color=COLORS["danger"], symbol="diamond"),
            name="Current",
        ))
    
    fig.update_layout(
        xaxis_title="UDI",
        yaxis=dict(title="Tool wear (min)", side="left"),
        yaxis2=dict(title="Risk score", side="right", overlaying="y", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    return fig.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# Empty figure
# ─────────────────────────────────────────────────────────────────────────────
def empty_figure(msg: str = "Waiting for data...") -> dict:
    """Placeholder figure when no data is available."""
    fig = go.Figure()
    fig.add_annotation(
        x=0.5, y=0.5,
        text=msg,
        showarrow=False,
        font=dict(size=14, color="gray"),
    )
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        paper_bgcolor="white",
        height=200,
    )
    return fig.to_dict()