"""
components/callbacks.py
All callbacks in a single file registered via function.

Applied patterns:
   - Store as single source of truth (no mutable globals)
   - Explicit PreventUpdate instead of returning no_update in normal flows
   - Error logging with complete traceback
   - Cache decorated only on load callback (data rarely changes)
"""

import logging
import traceback
import io

import pandas as pd
from dash import Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import html

from data.loader import (
    get_processed_data,
    compute_kpis,
    failure_by_type,
    failure_mode_distribution,
    TARGET_COL,
    TYPE_COL,
    FAILURE_MODES,
)
from components import figures

logger = logging.getLogger(__name__)


# ── Helpers de serialização ─────────────────────────────────────────────────────
def _to_json(df: pd.DataFrame) -> str:
    """Serializa DataFrame preservando tipos de dados importantes."""
    # Converter colunas categóricas para string para preservação
    df_serialized = df.copy()
    categorical_cols = df_serialized.select_dtypes(include=['category']).columns
    for col in categorical_cols:
        df_serialized[col] = df_serialized[col].astype(str)
    
    return df_serialized.to_json(orient="split", date_format="iso")

def _from_json(data: str) -> pd.DataFrame:
    """Deserializa DataFrame JSON e restaura tipos de dados."""
    if not data or data == "null":
        raise ValueError("Dados JSON vazios")
    
    df = pd.read_json(io.StringIO(data), orient="split")
    
    # Restaurar tipos conhecidos (baseado no schema do dataset)
    if 'Type' in df.columns:
        df['Type'] = df['Type'].astype('category')
    if 'Machine failure' in df.columns:
        df['Machine failure'] = df['Machine failure'].astype(int)
    
    return df


# ── Aplicar filtros ─────────────────────────────────────────────────────────────
def _filter(df: pd.DataFrame, type_val: str, wear: list, status: str) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    if type_val != "ALL":
        m &= df[TYPE_COL].astype(str) == type_val
    m &= df["Tool wear [min]"].between(wear[0], wear[1])
    if status == "FAIL":
        m &= df[TARGET_COL] == 1
    elif status == "OK":
        m &= df[TARGET_COL] == 0
    return df[m].copy()


# ── Registro principal ──────────────────────────────────────────────────────────
def register_callbacks(app, cache):
    
    # ── CB-10: Fullscreen Modals ───────────────────────────────────────────────
    # Scatter plot fullscreen
    @app.callback(
        Output("fullscreen-scatter-modal", "is_open"),
        Output("fullscreen-scatter-title", "children"),
        Output("fullscreen-scatter-graph", "figure"),
        Input("btn-fullscreen-scatter", "n_clicks"),
        Input("btn-close-fullscreen-scatter", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-scatter-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_scatter(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-scatter":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-scatter" and filtered_data:
            try:
                df = _from_json(filtered_data)
                fig = figures.scatter_torque_rpm(df)
                return True, "Scatter: Torque × Speed", fig
            except Exception as e:
                logger.error(f"Erro ao gerar scatter fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Failure modes fullscreen
    @app.callback(
        Output("fullscreen-failure-modes-modal", "is_open"),
        Output("fullscreen-failure-modes-title", "children"),
        Output("fullscreen-failure-modes-graph", "figure"),
        Input("btn-fullscreen-failure-modes", "n_clicks"),
        Input("btn-close-fullscreen-failure-modes", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-failure-modes-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_failure_modes(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-failure-modes":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-failure-modes" and filtered_data:
            try:
                df = _from_json(filtered_data)
                from data.loader import failure_mode_distribution
                dist_data = failure_mode_distribution(df)
                fig = figures.bar_failure_modes(dist_data)
                return True, "Failure Modes Distribution", fig
            except Exception as e:
                logger.error(f"Erro ao gerar failure modes fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Sensors fullscreen
    @app.callback(
        Output("fullscreen-sensors-modal", "is_open"),
        Output("fullscreen-sensors-title", "children"),
        Output("fullscreen-sensors-graph", "figure"),
        Input("btn-fullscreen-sensors", "n_clicks"),
        Input("btn-close-fullscreen-sensors", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-sensors-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_sensors(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-sensors":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-sensors" and filtered_data:
            try:
                df = _from_json(filtered_data)
                fig = figures.boxplot_sensors(df)
                return True, "Sensors by Status", fig
            except Exception as e:
                logger.error(f"Erro ao gerar sensors fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Chart by type fullscreen
    @app.callback(
        Output("fullscreen-chart-by-type-modal", "is_open"),
        Output("fullscreen-chart-by-type-title", "children"),
        Output("fullscreen-chart-by-type-graph", "figure"),
        Input("btn-fullscreen-chart-by-type", "n_clicks"),
        Input("btn-close-fullscreen-chart-by-type", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-chart-by-type-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_chart_by_type(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-chart-by-type":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-chart-by-type" and filtered_data:
            try:
                df = _from_json(filtered_data)
                from data.loader import failure_by_type
                type_data = failure_by_type(df)
                fig = figures.bar_by_type(type_data)
                return True, "Failure Rate by Product Type", fig
            except Exception as e:
                logger.error(f"Erro ao gerar chart by type fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Clientside callback for ESC key to close modals
    app.clientside_callback(
        """
        function(n_intervals) {
            // This is a placeholder - we'll use a different approach
            // Dash doesn't make global keyboard events easy to capture
            // For now, we rely on the close buttons
            return window.dash_clientside.no_update;
        }
        """,
        Output("dummy-output", "children"),
        Input("interval-refresh", "n_intervals"),
        prevent_initial_call=True
    )

    # ── CB-01: Carga inicial (memoizada por 5min) ───────────────────────────────
    @app.callback(
        Output("store-data",   "data"),
        Output("data-status",  "children"),
        Output("data-status",  "color"),
        Input("interval-refresh", "n_intervals"),
    )
    @cache.memoize(timeout=300)
    def cb_load_data(_n):
        """
        Carrega e processa o dataset (cache de 5 minutos para desenvolvimento).
        """
        try:
            logger.info("=== INÍCIO CB-01: Carregando dados ===")
            df = get_processed_data()
            logger.info("Dados carregados: %d linhas, %d colunas", len(df), len(df.columns))
            logger.info("Amostra de dados carregados:")
            logger.info("  - Colunas: %s", list(df.columns))
            logger.info("  - Tipos: %s", df.dtypes.to_dict())
            logger.info("  - Falhas: %d (%.2f%%)", 
                       df["Machine failure"].sum(), 
                       df["Machine failure"].mean() * 100)
            
            data_json = _to_json(df)
            logger.info("JSON serializado: %d bytes", len(data_json))
            logger.info("=== FIM CB-01: Dados carregados com sucesso ===")
            
            return data_json, f"{len(df):,} registros", "success"
        except Exception as exc:
            logger.error("=== ERRO CB-01: Falha ao carregar dados ===")
            logger.error("Detalhes: %s", traceback.format_exc())
            return no_update, "Erro ao carregar dados", "danger"


    # ── CB-02: Filtros → store-filtered ────────────────────────────────────────
    @app.callback(
        Output("store-filtered", "data"),
        Input("store-data",    "data"),
        Input("filter-type",   "value"),
        Input("filter-wear",   "value"),
        Input("filter-status", "value"),
        # Removed prevent_initial_call=True to allow initial trigger
    )
    def cb_apply_filters(raw, type_val, wear, status):
        if not raw:
            raise PreventUpdate
        try:
            df  = _from_json(raw)
            out = _filter(df, type_val, wear or [0, 250], status)
            logger.debug("Filtros → %d registros", len(out))
            return _to_json(out)
        except Exception:
            logger.error("Erro em cb_apply_filters:\n%s", traceback.format_exc())
            return no_update


    # ── CB-03: KPIs ─────────────────────────────────────────────────────────────
    @app.callback(
        Output("kpi-fail-rate",  "children"),
        Output("kpi-wear",       "children"),
        Output("kpi-main-mode",  "children"),
        Output("kpi-risk",       "children"),
        Input("store-filtered",  "data"),
        # Removed prevent_initial_call=True to allow initial trigger
    )
    def cb_kpis(fdata):
        if not fdata:
            raise PreventUpdate
        try:
            kpis = compute_kpis(_from_json(fdata))
            logger.debug("KPIs calculados: %s", kpis)
            return (
                f"{kpis['fail_rate_pct']}%",
                f"{kpis['wear_at_fail']} min",
                kpis["main_mode"],
                str(kpis["avg_risk"]),
            )
        except Exception:
            logger.error("Erro em cb_kpis:\n%s", traceback.format_exc())
            return "—", "—", "—", "—"


    # ── CB-04: Scatter ──────────────────────────────────────────────────────────
    @app.callback(
        Output("chart-scatter",  "figure"),
        Input("store-filtered",  "data"),
        # Removed prevent_initial_call=True to allow initial trigger
    )
    def cb_scatter(fdata):
        if not fdata:
            raise PreventUpdate
        try:
            fig = figures.scatter_torque_rpm(_from_json(fdata))
            logger.debug("Scatter gerado com sucesso")
            return fig
        except Exception:
            logger.error("Erro em cb_scatter:\n%s", traceback.format_exc())
            return figures.empty_figure("Erro ao renderizar scatter")


    # ── CB-05: Modos de falha ────────────────────────────────────────────────────
    @app.callback(
        Output("chart-failure-modes", "figure"),
        Input("store-filtered",       "data"),
        # Removed prevent_initial_call=True to allow initial trigger
    )
    def cb_failure_modes(fdata):
        if not fdata:
            raise PreventUpdate
        try:
            fig = figures.bar_failure_modes(failure_mode_distribution(_from_json(fdata)))
            logger.debug("Modos de falha gerados")
            return fig
        except Exception:
            logger.error("Erro em cb_failure_modes:\n%s", traceback.format_exc())
            return figures.empty_figure("Erro ao renderizar modos")


    # ── CB-06: Sensores ──────────────────────────────────────────────────────────
    @app.callback(
        Output("chart-sensors",  "figure"),
        Input("store-filtered",  "data"),
        # Removed prevent_initial_call=True to allow initial trigger
    )
    def cb_sensors(fdata):
        if not fdata:
            raise PreventUpdate
        try:
            fig = figures.boxplot_sensors(_from_json(fdata))
            logger.debug("Sensores gerados")
            return fig
        except Exception:
            logger.error("Erro em cb_sensors:\n%s", traceback.format_exc())
            return figures.empty_figure("Erro ao renderizar sensores")


    # ── CB-07: Falha por tipo ────────────────────────────────────────────────────
    @app.callback(
        Output("chart-by-type",  "figure"),
        Input("store-filtered",  "data"),
        # Removed prevent_initial_call=True to allow initial trigger
    )
    def cb_by_type(fdata):
        if not fdata:
            raise PreventUpdate
        try:
            fig = figures.bar_by_type(failure_by_type(_from_json(fdata)))
            logger.debug("Falha por tipo gerada")
            return fig
        except Exception:
            logger.error("Erro em cb_by_type:\n%s", traceback.format_exc())
            return figures.empty_figure("Erro")


    # ── CB-08: Alertas ───────────────────────────────────────────────────────────
    @app.callback(
        Output("alerts-list",   "children"),
        Output("badge-alerts",  "children"),
        Input("store-filtered", "data"),
        # Removed prevent_initial_call=True to allow initial trigger
    )
    def cb_alerts(fdata):
        if not fdata:
            raise PreventUpdate
        try:
            df = _from_json(fdata)
            alerts = df[
                (df["Risk score"] >= 0.65) | (df[TARGET_COL] == 1)
            ].sort_values("Risk score", ascending=False).head(25)

            count = len(alerts)
            logger.debug("Alertas encontrados: %d", count)
            if count == 0:
                return html.P("No active alerts.", className="text-muted small"), "0"

            items = []
            for _, row in alerts.iterrows():
                is_fail  = row[TARGET_COL] == 1
                severity = "danger" if is_fail else "warning"
                uid      = int(row.get("UDI", 0))
                wear     = int(row["Tool wear [min]"])
                risk     = float(row["Risk score"])
                items.append(
                    dbc.ListGroupItem([
                    dbc.Badge(
                        "FAILURE" if is_fail else "RISK",
                        color=severity, pill=True, className="me-2"
                    ),
                    html.Span(
                        f"UID {uid} · wear {wear} min · score {risk:.3f}",
                        className="small",
                    ),
                    ], action=True, className="py-1 px-2")
                )
            return dbc.ListGroup(items, flush=True), str(count)

        except Exception:
            logger.error("Erro em cb_alerts:\n%s", traceback.format_exc())
            return html.P("Error loading alerts", className="text-danger small"), "!"


    # ── CB-09: Modal drill-down ──────────────────────────────────────────────────
    @app.callback(
        Output("detail-modal",     "is_open"),
        Output("modal-title",      "children"),
        Output("modal-radar",      "figure"),
        Output("modal-history",    "figure"),
        Output("store-selected-uid", "data"),
        Input("chart-scatter",     "clickData"),
        Input("modal-close",       "n_clicks"),
        State("store-data",        "data"),
        State("detail-modal",      "is_open"),
        prevent_initial_call=True,
    )
    def cb_modal(click_data, _close, raw, is_open):
        triggered = callback_context.triggered_id

        if triggered == "modal-close":
            return False, no_update, no_update, no_update, no_update

        if triggered == "chart-scatter" and click_data and raw:
            try:
                point = click_data["points"][0]
                cd    = point.get("customdata")
                uid   = int(cd[0]) if cd else None
                df    = _from_json(raw)

                row = df[df["UDI"] == uid] if uid else df.iloc[[point.get("pointIndex", 0)]]
                if row.empty:
                    raise PreventUpdate

                r     = row.iloc[0]
                tipo  = r[TYPE_COL]
                stat  = "FAILURE" if r[TARGET_COL] else "OK"
                title = f"Equipment {uid}  ·  Type {tipo}  ·  Status: {stat}"

                return (
                    True,
                    title,
                    figures.radar_sensors(r, df),
                    figures.sensor_history(df, uid),
                    uid,
                )
            except PreventUpdate:
                raise
            except Exception:
                logger.error("Erro em cb_modal:\n%s", traceback.format_exc())
                raise PreventUpdate

        raise PreventUpdate

    # ── CB-10: Fullscreen Modals ───────────────────────────────────────────────
    # Scatter plot fullscreen
    @app.callback(
        Output("fullscreen-scatter-modal", "is_open"),
        Output("fullscreen-scatter-title", "children"),
        Output("fullscreen-scatter-graph", "figure"),
        Input("btn-fullscreen-scatter", "n_clicks"),
        Input("btn-close-fullscreen-scatter", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-scatter-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_scatter(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-scatter":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-scatter" and filtered_data:
            try:
                df = _from_json(filtered_data)
                fig = figures.scatter_torque_rpm(df)
                return True, "Scatter: Torque × Speed", fig
            except Exception as e:
                logger.error(f"Erro ao gerar scatter fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Failure modes fullscreen
    @app.callback(
        Output("fullscreen-failure-modes-modal", "is_open"),
        Output("fullscreen-failure-modes-title", "children"),
        Output("fullscreen-failure-modes-graph", "figure"),
        Input("btn-fullscreen-failure-modes", "n_clicks"),
        Input("btn-close-fullscreen-failure-modes", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-failure-modes-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_failure_modes(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-failure-modes":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-failure-modes" and filtered_data:
            try:
                df = _from_json(filtered_data)
                from data.loader import failure_mode_distribution
                dist_data = failure_mode_distribution(df)
                fig = figures.bar_failure_modes(dist_data)
                return True, "Failure Modes Distribution", fig
            except Exception as e:
                logger.error(f"Erro ao gerar failure modes fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Sensors fullscreen
    @app.callback(
        Output("fullscreen-sensors-modal", "is_open"),
        Output("fullscreen-sensors-title", "children"),
        Output("fullscreen-sensors-graph", "figure"),
        Input("btn-fullscreen-sensors", "n_clicks"),
        Input("btn-close-fullscreen-sensors", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-sensors-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_sensors(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-sensors":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-sensors" and filtered_data:
            try:
                df = _from_json(filtered_data)
                fig = figures.boxplot_sensors(df)
                return True, "Sensors by Status", fig
            except Exception as e:
                logger.error(f"Erro ao gerar sensors fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Chart by type fullscreen
    @app.callback(
        Output("fullscreen-chart-by-type-modal", "is_open"),
        Output("fullscreen-chart-by-type-title", "children"),
        Output("fullscreen-chart-by-type-graph", "figure"),
        Input("btn-fullscreen-chart-by-type", "n_clicks"),
        Input("btn-close-fullscreen-chart-by-type", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-chart-by-type-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_chart_by_type(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-chart-by-type":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-chart-by-type" and filtered_data:
            try:
                df = _from_json(filtered_data)
                from data.loader import failure_by_type
                type_data = failure_by_type(df)
                fig = figures.bar_by_type(type_data)
                return True, "Failure Rate by Product Type", fig
            except Exception as e:
                logger.error(f"Erro ao gerar chart by type fullscreen: {e}")
                return is_open, no_update, no_update
        return is_open, no_update, no_update

    # Add a simple interval for potential future keyboard handling
    @app.callback(
        Output("dummy-output", "children"),
        Input("interval-refresh", "n_intervals"),
        prevent_initial_call=True
    )
    def dummy_callback(n):
        return ""

    # ── CB-10: Fullscreen Modals ───────────────────────────────────────────────
    # Scatter plot fullscreen
    @app.callback(
        Output("fullscreen-scatter-modal", "is_open"),
        Output("fullscreen-scatter-title", "children"),
        Output("fullscreen-scatter-graph", "figure"),
        Input("btn-fullscreen-scatter", "n_clicks"),
        Input("btn-close-fullscreen-scatter", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-scatter-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_scatter(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-scatter":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-scatter" and filtered_data:
            try:
                df = _from_json(filtered_data)
                fig = figures.scatter_torque_rpm(df)
                return True, "Scatter: Torque × Speed", fig
            except Exception as e:
                logger.error(f"Erro ao gerar scatter fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Failure modes fullscreen
    @app.callback(
        Output("fullscreen-failure-modes-modal", "is_open"),
        Output("fullscreen-failure-modes-title", "children"),
        Output("fullscreen-failure-modes-graph", "figure"),
        Input("btn-fullscreen-failure-modes", "n_clicks"),
        Input("btn-close-fullscreen-failure-modes", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-failure-modes-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_failure_modes(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-failure-modes":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-failure-modes" and filtered_data:
            try:
                df = _from_json(filtered_data)
                from data.loader import failure_mode_distribution
                dist_data = failure_mode_distribution(df)
                fig = figures.bar_failure_modes(dist_data)
                return True, "Failure Modes Distribution", fig
            except Exception as e:
                logger.error(f"Erro ao gerar failure modes fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Sensors fullscreen
    @app.callback(
        Output("fullscreen-sensors-modal", "is_open"),
        Output("fullscreen-sensors-title", "children"),
        Output("fullscreen-sensors-graph", "figure"),
        Input("btn-fullscreen-sensors", "n_clicks"),
        Input("btn-close-fullscreen-sensors", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-sensors-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_sensors(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-sensors":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-sensors" and filtered_data:
            try:
                df = _from_json(filtered_data)
                fig = figures.boxplot_sensors(df)
                return True, "Sensors by Status", fig
            except Exception as e:
                logger.error(f"Erro ao gerar sensors fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Chart by type fullscreen
    @app.callback(
        Output("fullscreen-chart-by-type-modal", "is_open"),
        Output("fullscreen-chart-by-type-title", "children"),
        Output("fullscreen-chart-by-type-graph", "figure"),
        Input("btn-fullscreen-chart-by-type", "n_clicks"),
        Input("btn-close-fullscreen-chart-by-type", "n_clicks"),
        State("store-filtered", "data"),
        State("fullscreen-chart-by-type-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_fullscreen_chart_by_type(open_click, close_click, filtered_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open, no_update, no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "btn-close-fullscreen-chart-by-type":
            return False, no_update, no_update
        
        if trigger_id == "btn-fullscreen-chart-by-type" and filtered_data:
            try:
                df = _from_json(filtered_data)
                from data.loader import failure_by_type
                type_data = failure_by_type(df)
                fig = figures.bar_by_type(type_data)
                return True, "Failure Rate by Product Type", fig
            except Exception as e:
                logger.error(f"Erro ao gerar chart by type fullscreen: {e}")
                return is_open, no_update, no_update
        
        return is_open, no_update, no_update

    # Add a simple interval for potential future keyboard handling
    @app.callback(
        Output("dummy-output", "children"),
        Input("interval-refresh", "n_intervals"),
        prevent_initial_call=True
    )
    def dummy_callback(n):
        return ""
