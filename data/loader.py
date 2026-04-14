"""
data/loader.py
Complete pipeline: ingestion → cleaning → feature engineering → aggregations.
Primary source: UCI ML Repository (ucimlrepo).
Fallback: Local CSV in data/ai4i2020.csv
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Constantes ─────────────────────────────────────────────────────────────────
DATA_DIR       = Path(__file__).parent
CSV_PATH       = DATA_DIR / "ai4i2020.csv"
UCI_DATASET_ID = 601

SENSOR_COLS = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]
FAILURE_MODES = ["TWF", "HDF", "PWF", "OSF", "RNF"]
TARGET_COL    = "Machine failure"
TYPE_COL      = "Type"


# ── 1. Carregamento ─────────────────────────────────────────────────────────────
def load_raw() -> pd.DataFrame:
    """
    Attempts UCI → saves local CSV as cache → uses local CSV in subsequent executions.
    Raises RuntimeError if no source is available.
    """
    if CSV_PATH.exists():
        logger.info("Loading local CSV: %s", CSV_PATH)
        df = pd.read_csv(CSV_PATH)
        # Map CSV column names to expected names with units for consistency
        column_mapping = {
            "Air temperature": "Air temperature [K]",
            "Process temperature": "Process temperature [K]",
            "Rotational speed": "Rotational speed [rpm]",
            "Torque": "Torque [Nm]",
            "Tool wear": "Tool wear [min]",
        }
        df = df.rename(columns=column_mapping)
        return df

    try:
        from ucimlrepo import fetch_ucirepo
        logger.info("Downloading UCI dataset id=%s …", UCI_DATASET_ID)
        repo = fetch_ucirepo(id=UCI_DATASET_ID)
        df   = pd.concat([repo.data.features, repo.data.targets], axis=1)
        df.to_csv(CSV_PATH, index=False)
        logger.info("Dataset saved in %s (%d lines)", CSV_PATH, len(df))
        return df
    except Exception as exc:
        raise RuntimeError(
            "Place ai4i2020.csv in data/ or check internet connection."
        ) from exc


# ── 2. Limpeza ──────────────────────────────────────────────────────────────────
def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Remove duplicates
    - Fix label noise (subtype active but Machine failure = 0)
    - Correct typing
    - Add synthetic UDI (unique ID)
    """
    before = len(df)
    df = df.drop_duplicates().copy()
    if len(df) < before:
        logger.warning("Removed %d duplicate rows", before - len(df))

    # Label noise: some subtype = 1 but target = 0
    noise = (df[FAILURE_MODES].sum(axis=1) > 0) & (df[TARGET_COL] == 0)
    if noise.sum():
        df.loc[noise, TARGET_COL] = 1
        logger.warning("Label noise fixed in %d records", noise.sum())

    df[TYPE_COL]   = df[TYPE_COL].astype("category")
    df[TARGET_COL] = df[TARGET_COL].astype(int)
    for col in FAILURE_MODES:
        df[col] = df[col].astype(int)

    # Add synthetic UDI (sequential unique ID)
    df["UDI"] = range(1, len(df) + 1)
    logger.info("Added synthetic UDI (1-%d)", len(df))

    logger.info("Cleaning OK — %d valid records", len(df))
    return df


# ── 3. Feature Engineering ──────────────────────────────────────────────────────
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates derived variables with physical meaning:
      Power [W]     = Torque × RPM          → detect overload
      Temp diff [K] = Process − Air          → proxy of heat dissipation
      Wear rate     = Tool wear / (RPM + 1)  → wear rate relative
      Risk score    = heuristic 0-1          → replaced by ML in Phase 5
    """
    df = df.copy()

    df["Power [W]"]     = df["Torque [Nm]"] * df["Rotational speed [rpm]"]
    df["Temp diff [K]"] = df["Process temperature [K]"] - df["Air temperature [K]"]
    df["Wear rate"]     = df["Tool wear [min]"] / (df["Rotational speed [rpm]"] + 1)

    # Normalized heuristic score (proxy until ML model is available)
    w = df["Tool wear [min]"]  / df["Tool wear [min]"].max()
    p = df["Power [W]"]        / df["Power [W]"].max()
    t = df["Temp diff [K]"]    / df["Temp diff [K]"].max()
    df["Risk score"] = (0.5 * w + 0.3 * p + 0.2 * t).round(4)

    return df


# ── 4. Agregações para gráficos ─────────────────────────────────────────────────
def compute_kpis(df: pd.DataFrame) -> dict:
    total     = len(df)
    failures  = int(df[TARGET_COL].sum())
    fail_rate = round(failures / total * 100, 2) if total else 0.0
    wear_fail = df.loc[df[TARGET_COL] == 1, "Tool wear [min]"].mean()
    mode_cts  = {m: int(df[m].sum()) for m in FAILURE_MODES}
    main_mode = max(mode_cts, key=mode_cts.get)
    avg_risk  = round(float(df["Risk score"].mean()), 3)

    return {
        "total":         total,
        "failures":      failures,
        "fail_rate_pct": fail_rate,
        "wear_at_fail":  round(float(wear_fail), 1) if not np.isnan(wear_fail) else 0,
        "main_mode":     main_mode,
        "mode_counts":   mode_cts,
        "avg_risk":      avg_risk,
    }


def failure_by_type(df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby(TYPE_COL, observed=True)[TARGET_COL]
    return (grp.mean().mul(100).round(2)
            .reset_index()
            .rename(columns={TARGET_COL: "fail_rate_pct"}))


def failure_mode_distribution(df: pd.DataFrame) -> pd.DataFrame:
    counts = {m: int(df[m].sum()) for m in FAILURE_MODES}
    total  = sum(counts.values()) or 1
    return pd.DataFrame({
        "mode":  list(counts.keys()),
        "count": list(counts.values()),
        "pct":   [round(v / total * 100, 1) for v in counts.values()],
    }).sort_values("count", ascending=False)


# ── 5. Pipeline público ─────────────────────────────────────────────────────────
def get_processed_data() -> pd.DataFrame:
    """Ponto de entrada único — load → clean → engineer."""
    df = load_raw()
    df = clean(df)
    df = engineer_features(df)
    logger.info("Pipeline concluído. Shape: %s", df.shape)
    return df
