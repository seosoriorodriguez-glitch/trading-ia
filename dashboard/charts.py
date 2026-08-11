# -*- coding: utf-8 -*-
"""
Figuras Plotly para el dashboard: candlestick + zonas OB + trades, y curva de equity.
Patron reutilizado de visualize_backtest.py (add_shape rect para zonas). Codigo nuevo.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_BULL = "rgba(38,166,91,0.12)"    # verde suave
_BEAR = "rgba(231,76,60,0.12)"    # rojo suave


def candles_zones_trades(df5, zones, results, focus_time=None, window=220, default_bars=320):
    """Candlestick M5 + cajas de zonas OB + marcadores de trades (entry/SL/TP, verde/rojo).
    Si focus_time se da, hace zoom a ~window velas alrededor de ese trade (ideal para debug)."""
    d = df5.reset_index(drop=True)
    if focus_time is not None:
        focus_time = pd.to_datetime(focus_time)
        i = int((d.time - focus_time).abs().values.argmin())
        lo = max(0, i - window // 2)
        hi = min(len(d), i + window // 2)
        d = d.iloc[lo:hi]
    else:
        d = d.tail(default_bars)
    if d.empty:
        return go.Figure()

    x0, x1 = d.time.iloc[0], d.time.iloc[-1]
    ylo, yhi = float(d.low.min()), float(d.high.max())

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=d.time, open=d.open, high=d.high, low=d.low, close=d.close,
        name="M5", increasing_line_color="#26a65b", decreasing_line_color="#e74c3c"))

    # zonas OB visibles en la ventana (confirmadas antes de x1 y con solape de precio)
    for z in zones:
        conf = pd.to_datetime(z.confirmed_at)
        if conf > x1:
            continue
        if z.zone_high < ylo or z.zone_low > yhi:
            continue
        fig.add_shape(
            type="rect", xref="x", yref="y", layer="below",
            x0=max(conf, x0), x1=x1, y0=z.zone_low, y1=z.zone_high,
            fillcolor=_BULL if z.ob_type == "bullish" else _BEAR,
            line=dict(width=0))

    # trades dentro de la ventana
    if results is not None and not results.empty:
        r = results.copy()
        r["entry_time"] = pd.to_datetime(r["entry_time"])
        r["exit_time"] = pd.to_datetime(r["exit_time"])
        r = r[(r.entry_time >= x0) & (r.entry_time <= x1)]
        for _, t in r.iterrows():
            win = t.pnl_r > 0
            col = "#26a65b" if win else "#e74c3c"
            xend = t.exit_time if pd.notna(t.exit_time) else x1
            # SL y TP como lineas punteadas del entry al exit
            fig.add_shape(type="line", x0=t.entry_time, x1=xend, y0=t.sl, y1=t.sl,
                          line=dict(color="#e74c3c", width=1, dash="dot"))
            fig.add_shape(type="line", x0=t.entry_time, x1=xend, y0=t.tp, y1=t.tp,
                          line=dict(color="#26a65b", width=1, dash="dot"))
            # marcador de entrada
            fig.add_trace(go.Scatter(
                x=[t.entry_time], y=[t.entry_price], mode="markers",
                marker=dict(size=11, color=col,
                            symbol="triangle-up" if t.direction == "long" else "triangle-down"),
                showlegend=False,
                hovertext=f"{t.direction} {t.pnl_r:+.2f}R ({t.exit_reason})",
                hoverinfo="text"))

    fig.update_layout(
        xaxis_rangeslider_visible=False, height=560,
        margin=dict(l=0, r=0, t=24, b=0),
        dragmode="pan", hovermode="x")
    return fig


def equity_curve(results):
    """Curva de equity (balance por trade) + drawdown % debajo."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.04)
    if results is None or results.empty:
        return fig
    r = results.sort_values("exit_time").reset_index(drop=True)
    r["exit_time"] = pd.to_datetime(r["exit_time"])
    peak = r.balance.cummax()
    dd = (peak - r.balance) / peak * 100
    fig.add_trace(go.Scatter(x=r.exit_time, y=r.balance, mode="lines",
                             line=dict(color="#2E86DE", width=2), name="Equity"), row=1, col=1)
    fig.add_trace(go.Scatter(x=r.exit_time, y=dd, mode="lines", fill="tozeroy",
                             line=dict(color="#e74c3c", width=1), name="DD %"), row=2, col=1)
    fig.update_yaxes(title_text="Balance", row=1, col=1)
    fig.update_yaxes(title_text="DD %", autorange="reversed", row=2, col=1)
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
    return fig


def equity_overlay(runs_results):
    """Superpone curvas de equity normalizadas (%) de varios runs. runs_results: list[(label, df)]."""
    fig = go.Figure()
    for label, res in runs_results:
        if res is None or res.empty:
            continue
        r = res.sort_values("exit_time").reset_index(drop=True)
        base = r.balance.iloc[0] if len(r) else 100000
        pct = (r.balance / base - 1) * 100
        fig.add_trace(go.Scatter(x=pd.to_datetime(r.exit_time), y=pct, mode="lines", name=label))
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=20, b=0),
                      yaxis_title="Retorno %", legend=dict(orientation="h"))
    return fig
