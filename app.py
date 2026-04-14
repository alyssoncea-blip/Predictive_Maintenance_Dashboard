"""
Predictive Maintenance Dashboard — AI4I 2020
Entry point da aplicação Dash.
"""

import logging
import dash
import dash_bootstrap_components as dbc

from components.layout import build_layout
from components.callbacks import register_callbacks
from utils.logger import setup_logger
from utils.cache import configure_cache

logger = setup_logger(__name__)

# ── Inicialização do app ───────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP, 
        "/assets/style.css",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True,   # necessário para callbacks em tabs dinâmicas
    title="PdM Dashboard",
    update_title=None,
)

server = app.server          # expõe WSGI Flask para Gunicorn / Render / Railway

# ── Cache via Flask-Caching ────────────────────────────────────────────────────
cache = configure_cache(server)

# ── Layout e callbacks ─────────────────────────────────────────────────────────
app.layout = build_layout()
register_callbacks(app, cache)

if __name__ == "__main__":
    logger.info("Iniciando PdM Dashboard — modo produção")
    app.run(debug=False, host="localhost", port=8050)
