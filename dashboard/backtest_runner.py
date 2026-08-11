# -*- coding: utf-8 -*-
"""
Wrapper LLAMABLE del motor Order Block para el dashboard interno.

100% ADITIVO: solo IMPORTA el motor de produccion en modo lectura, no modifica nada.
`journal/analysis/ob_multiasset.py` es un script (corre al importarse), asi que aqui se
REPLICA su logica (ASSETS, SESSIONS, escalado de params, metricas) como funciones.
"""
import sys
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester
from strategies.order_block.backtest.ob_detection import detect_order_blocks
import strategies.order_block.backtest.signals as _signals

DATA = ROOT / "data"
_ORIG_SESSION_FN = _signals.is_session_allowed  # para restaurar tras runs 24_7

# activo -> (csv_M5, csv_M1, spread_default_en_puntos_precio)  [replica de ob_multiasset]
ASSETS = {
    "US30":     ("US30_icm_M5_518d.csv",      "US30_icm_M1_500k.csv",    3.0),
    "US30_F":   ("US30_icm_M5_fresh.csv",     "US30_icm_M1_fresh.csv",   2.0),
    "XAUUSD":   ("XAUUSD_icm_M5.csv",         "XAUUSD_icm_M1.csv",       0.20),
    "XAUUSD_F": ("XAUUSD_icm_M5_fresh.csv",   "XAUUSD_icm_M1_fresh.csv", 0.40),
    "DE40":     ("DE40_icm_M5.csv",           "DE40_icm_M1.csv",         1.5),
    "GBPUSD":   ("GBPUSD_icm_M5.csv",         "GBPUSD_icm_M1.csv",       0.00015),
    "GBPJPY":   ("GBPJPY_icm_M5.csv",         "GBPJPY_icm_M1.csv",       0.02),
    "XAGUSD":   ("XAGUSD_icm_M5.csv",         "XAGUSD_icm_M1.csv",       0.025),
    "BTCUSD":   ("BTCUSD_icm_M5.csv",         "BTCUSD_icm_M1.csv",       20.0),
    "USDJPY":   ("USDJPY_icm_M5.csv",         "USDJPY_icm_M1.csv",       0.012),
    "CADJPY":   ("CADJPY_icm_M5.csv",         "CADJPY_icm_M1.csv",       0.018),
    "EURCHF":   ("EURCHF_icm_M5.csv",         "EURCHF_icm_M1.csv",       0.00015),
    "US2000":   ("US2000_icm_M5.csv",         "US2000_icm_M1.csv",       0.15),
}

SESSIONS = {
    "london": {"london":   {"start": "10:00", "end": "17:00", "skip_minutes": 15}},
    "ny":     {"new_york":  {"start": "13:30", "end": "23:00", "skip_minutes": 15}},
    "both":   {"london":    {"start": "10:00", "end": "17:00", "skip_minutes": 15},
               "new_york":  {"start": "13:30", "end": "23:00", "skip_minutes": 15}},
    "24_7":   {"all":       {"start": "00:00", "end": "23:59", "skip_minutes": 0}},
}


def list_assets():
    """Activos de ASSETS cuyos CSV M5 y M1 existen en data/."""
    out = []
    for name, (m5, m1, _sp) in ASSETS.items():
        if (DATA / m5).exists() and (DATA / m1).exists():
            out.append(name)
    return out


def default_spread(asset):
    return ASSETS.get(asset, (None, None, 0.0))[2]


def _scale_params(med, spread, session, rr, risk_pct):
    """Escalado por instrumento (ratios calibrados vs US30, med~19.6) — igual que ob_multiasset."""
    p = copy.deepcopy(DEFAULT_PARAMS)
    p["min_risk_points"]   = round(med * 0.765, 5)
    p["buffer_points"]     = round(med * 1.276, 5)
    p["max_risk_points"]   = round(med * 15.3, 5)
    p["avg_spread_points"] = spread
    p["slippage_points"]   = round(med * 0.10, 5)
    p["sessions"]          = SESSIONS[session]
    p["target_rr"]         = float(rr)
    p["risk_per_trade_pct"] = float(risk_pct)
    p["initial_balance"]   = 100_000.0
    return p


def _pf(x):
    g = x[x > 0].sum()
    l = abs(x[x <= 0].sum())
    return float(g / l) if l > 0 else 99.0


def _metrics(res, bt, med, risk_pct):
    if res is None or res.empty:
        return {"n_trades": 0, "trades_month": 0, "wr": 0, "pf": 0, "pf_1h": 0, "pf_2h": 0,
                "robust": False, "sumR": 0, "return_pct": 0, "dd_pct": 0, "days": 0,
                "med": round(med, 4), "annual_pct": 0, "final_balance": round(bt.balance, 2)}
    r = res.sort_values("exit_time").reset_index(drop=True)
    n = len(r)
    wr = float((r.pnl_r > 0).mean() * 100)
    PF = _pf(r.pnl_r)
    mid = n // 2
    p1, p2 = _pf(r.pnl_r.iloc[:mid]), _pf(r.pnl_r.iloc[mid:])
    sumR = float(r.pnl_r.sum())
    ret = (bt.balance - bt.initial_balance) / bt.initial_balance * 100
    cum = r.pnl_r.cumsum()
    ddR = float((cum.cummax() - cum).max())
    days = max((pd.to_datetime(r.exit_time).max() - pd.to_datetime(r.entry_time).min()).days, 1)
    return {
        "n_trades": n,
        "trades_month": round(n / days * 30, 1),
        "wr": round(wr, 1),
        "pf": round(PF, 2),
        "pf_1h": round(p1, 2),
        "pf_2h": round(p2, 2),
        "robust": bool(PF > 1 and p1 > 1 and p2 > 1),
        "sumR": round(sumR, 1),
        "return_pct": round(ret, 1),
        "dd_pct": round(ddR * risk_pct * 100, 1),   # ddR (en R) * riesgo% por trade
        "days": days,
        "med": round(med, 4),
        "annual_pct": round(ret / days * 365, 0),
        "final_balance": round(bt.balance, 2),
    }


def _load_trimmed(asset):
    """Carga M5 recortado al rango del M1 (igual que ob_multiasset). Devuelve df5, m1_range."""
    m5, m1, _sp = ASSETS[asset]
    df5 = load_csv(str(DATA / m5))
    df1 = load_csv(str(DATA / m1))
    t0, t1 = df1.time.iloc[0], df1.time.iloc[-1]
    df5 = df5[(df5.time >= t0) & (df5.time <= t1)].reset_index(drop=True)
    return df5, df1, t0, t1


def run_backtest(asset, session="both", spread=None, rr=2.5, risk_pct=0.005):
    """Corre el motor real M5+M1 y devuelve todo lo que el dashboard necesita."""
    sp = default_spread(asset) if spread is None else float(spread)
    df5, df1, t0, t1 = _load_trimmed(asset)
    med = float((df5.high - df5.low).median())
    p = _scale_params(med, sp, session, rr, risk_pct)

    # sesion 24_7 (cripto): permitir todo. SIEMPRE restaurar despues (proceso persistente).
    if session == "24_7":
        _signals.is_session_allowed = lambda dt, params: True
    else:
        _signals.is_session_allowed = _ORIG_SESSION_FN
    try:
        bt = OrderBlockBacktester(p)
        res = bt.run(df5, df1)
    finally:
        _signals.is_session_allowed = _ORIG_SESSION_FN

    zones = detect_order_blocks(df5, p)
    metrics = _metrics(res, bt, med, risk_pct)
    config = {
        "asset": asset, "session": session, "spread": sp, "rr": float(rr),
        "risk_pct": float(risk_pct),
        "m1_start": str(t0), "m1_end": str(t1),
    }
    return {"results": res, "metrics": metrics, "df5": df5, "zones": zones,
            "params": p, "config": config}


def chart_data(config):
    """Para recargar el grafico de un run guardado SIN correr el loop M1 (rapido):
    solo carga M5 + detecta zonas. Los trades vienen del CSV guardado."""
    asset = config["asset"]
    m5, _m1, _sp = ASSETS[asset]
    df5 = load_csv(str(DATA / m5))
    t0 = pd.to_datetime(config["m1_start"])
    t1 = pd.to_datetime(config["m1_end"])
    df5 = df5[(df5.time >= t0) & (df5.time <= t1)].reset_index(drop=True)
    med = float((df5.high - df5.low).median())
    p = _scale_params(med, config["spread"], config["session"], config["rr"], config["risk_pct"])
    zones = detect_order_blocks(df5, p)
    return {"df5": df5, "zones": zones, "params": p}
