# -*- coding: utf-8 -*-
"""
Visualizacion interactiva del backtest Bot 2 London.
Genera un HTML autocontenido con Plotly.

Uso: python visualize_backtest.py
     python visualize_backtest.py --no-candles   (sin panel de velas, mas rapido)
"""
import sys, argparse
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

parser = argparse.ArgumentParser()
parser.add_argument("--no-candles", action="store_true", help="Omitir panel de velas M5")
parser.add_argument("--days", type=int, default=30, help="Dias a mostrar en panel velas (default: 30)")
args = parser.parse_args()

RESULTS_DIR = Path("strategies/order_block_london/backtest/results")
OUT_FILE    = Path("strategies/order_block_london/backtest/results/backtest_report.html")

# ----------------------------------------------------------------
# Cargar datos
# ----------------------------------------------------------------
print("Cargando archivos...")
trades = pd.read_csv(RESULTS_DIR / "trades.csv", parse_dates=["entry_time", "exit_time"])
equity = pd.read_csv(RESULTS_DIR / "equity.csv", parse_dates=["timestamp"])
obs    = pd.read_csv(RESULTS_DIR / "ob_zones.csv", parse_dates=["confirmed_at", "entry_time", "exit_time"])
print(f"  Trades: {len(trades)} | Equity: {len(equity):,} | OBs: {len(obs):,}")

# ----------------------------------------------------------------
# Metricas
# ----------------------------------------------------------------
winners  = trades[trades["pnl_usd"] > 0]
losers   = trades[trades["pnl_usd"] < 0]
n        = len(trades)
wr       = len(winners) / n * 100
pf       = winners["pnl_usd"].sum() / abs(losers["pnl_usd"].sum()) if len(losers) > 0 else 999
max_dd   = equity["drawdown_pct"].max()
exp      = trades["pnl_usd"].mean()
avg_win  = winners["pnl_usd"].mean() if len(winners) > 0 else 0
avg_loss = losers["pnl_usd"].mean()  if len(losers) > 0 else 0
best     = trades["pnl_usd"].max()
worst    = trades["pnl_usd"].min()
total    = trades["pnl_usd"].sum()
ret_pct  = total / 10_000 * 100

# Sharpe (diario)
daily_pnl = trades.groupby(trades["entry_time"].dt.date)["pnl_usd"].sum()
sharpe = (daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)) if daily_pnl.std() > 0 else 0

# ----------------------------------------------------------------
# Layout: 5 panels (o 4 sin velas)
# ----------------------------------------------------------------
n_panels = 4 if args.no_candles else 5
row_heights = [0.30, 0.20, 0.15, 0.20] if args.no_candles else [0.25, 0.15, 0.12, 0.18, 0.30]

specs = [[{"type": "scatter"}],
         [{"type": "histogram"}],
         [{"type": "table"}],
         [{"type": "heatmap"}]]
if not args.no_candles:
    specs.append([{"type": "candlestick"}])

titles = [
    "Panel 1 — Equity Curve & Drawdown",
    "Panel 2 — Distribucion de PnL por Trade",
    "Panel 3 — Metricas Resumen",
    "Panel 4 — Heatmap PnL por Hora y Dia",
]
if not args.no_candles:
    titles.append("Panel 5 — Velas M5 con OBs y Trades")

fig = make_subplots(
    rows=n_panels, cols=1,
    subplot_titles=titles,
    row_heights=row_heights,
    vertical_spacing=0.06,
    specs=specs,
)

# ----------------------------------------------------------------
# Panel 1 — Equity Curve
# ----------------------------------------------------------------
print("Generando Panel 1 — Equity Curve...")

# Downsample equity a 1 punto cada 15 min para no pesar demasiado
equity_ds = equity.set_index("timestamp").resample("15min").last().dropna().reset_index()

fig.add_trace(go.Scatter(
    x=equity_ds["timestamp"],
    y=equity_ds["balance"],
    mode="lines",
    name="Balance",
    line=dict(color="#00d4aa", width=1.5),
    hovertemplate="<b>%{x}</b><br>Balance: $%{y:,.2f}<extra></extra>",
), row=1, col=1)

# Drawdown sombreado
dd_y_top = equity_ds["balance"]
dd_y_bot = equity_ds["balance"] * (1 - equity_ds["drawdown_pct"] / 100)
fig.add_trace(go.Scatter(
    x=pd.concat([equity_ds["timestamp"], equity_ds["timestamp"][::-1]]),
    y=pd.concat([dd_y_top, dd_y_bot[::-1]]),
    fill="toself",
    fillcolor="rgba(255,50,50,0.15)",
    line=dict(color="rgba(255,50,50,0)"),
    name="Drawdown",
    hoverinfo="skip",
), row=1, col=1)

# Linea capital inicial
fig.add_hline(y=10_000, line_dash="dash", line_color="gray",
              annotation_text="Capital inicial $10,000", row=1, col=1)

# ----------------------------------------------------------------
# Panel 2 — Histograma PnL
# ----------------------------------------------------------------
print("Generando Panel 2 — Histograma PnL...")

fig.add_trace(go.Histogram(
    x=winners["pnl_usd"],
    name="Winners",
    marker_color="#00d4aa",
    opacity=0.8,
    nbinsx=40,
    hovertemplate="PnL: $%{x:.0f}<br>Trades: %{y}<extra>Winner</extra>",
), row=2, col=1)

fig.add_trace(go.Histogram(
    x=losers["pnl_usd"],
    name="Losers",
    marker_color="#ff4444",
    opacity=0.8,
    nbinsx=40,
    hovertemplate="PnL: $%{x:.0f}<br>Trades: %{y}<extra>Loser</extra>",
), row=2, col=1)

fig.add_vline(x=0, line_dash="dash", line_color="white", row=2, col=1)

# ----------------------------------------------------------------
# Panel 3 — Tabla de metricas
# ----------------------------------------------------------------
print("Generando Panel 3 — Metricas...")

metrics_labels = [
    "Total Trades", "Win Rate", "Profit Factor", "Expectancy",
    "Total PnL", "Retorno", "Max Drawdown", "Sharpe Ratio",
    "Avg Winner", "Avg Loser", "Mejor Trade", "Peor Trade",
]
metrics_values = [
    f"{n}",
    f"{wr:.1f}%",
    f"{pf:.2f}",
    f"${exp:+,.2f}",
    f"${total:+,.0f}",
    f"{ret_pct:+.1f}%",
    f"{max_dd:.2f}%",
    f"{sharpe:.2f}",
    f"${avg_win:+,.2f}",
    f"${avg_loss:+,.2f}",
    f"${best:+,.2f}",
    f"${worst:+,.2f}",
]

# Split en 2 columnas
mid = len(metrics_labels) // 2
fig.add_trace(go.Table(
    header=dict(
        values=["<b>Metrica</b>", "<b>Valor</b>", "<b>Metrica</b>", "<b>Valor</b>"],
        fill_color="#1e2130",
        font=dict(color="white", size=12),
        align="left",
        height=28,
    ),
    cells=dict(
        values=[
            metrics_labels[:mid],
            metrics_values[:mid],
            metrics_labels[mid:],
            metrics_values[mid:],
        ],
        fill_color=[["#13151f", "#1a1d2e"] * mid],
        font=dict(color=["#aaaaaa", "#00d4aa"] * 2, size=11),
        align="left",
        height=24,
    ),
), row=3, col=1)

# ----------------------------------------------------------------
# Panel 4 — Heatmap PnL por hora y dia semana
# ----------------------------------------------------------------
print("Generando Panel 4 — Heatmap...")

trades["hour"] = trades["entry_time"].dt.hour
trades["weekday"] = trades["entry_time"].dt.weekday  # 0=Lun, 4=Vie

pivot = trades.pivot_table(
    values="pnl_usd",
    index="weekday",
    columns="hour",
    aggfunc="sum",
    fill_value=0,
)

day_names  = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
hour_labels = [f"{h:02d}:00" for h in pivot.columns]
day_labels  = [day_names[d] for d in pivot.index if d < 5]

fig.add_trace(go.Heatmap(
    z=pivot.values,
    x=hour_labels,
    y=day_labels,
    colorscale=[
        [0.0, "#ff2222"],
        [0.5, "#1a1d2e"],
        [1.0, "#00d4aa"],
    ],
    zmid=0,
    name="PnL por hora",
    hovertemplate="<b>%{y} %{x}</b><br>PnL: $%{z:,.0f}<extra></extra>",
    colorbar=dict(title="PnL $", thickness=12, len=0.25, y=0.18),
), row=4, col=1)

# ----------------------------------------------------------------
# Panel 5 — Velas M5 con OBs y Trades (opcional)
# ----------------------------------------------------------------
if not args.no_candles:
    print(f"Generando Panel 5 — Velas M5 (ultimos {args.days} dias)...")

    from strategies.order_block.backtest.data_loader import load_csv
    df_m5 = load_csv("data/US30_icm_M5_518d.csv")

    cutoff = df_m5["time"].max() - pd.Timedelta(days=args.days)
    df_plot = df_m5[df_m5["time"] >= cutoff].copy()

    # Velas
    fig.add_trace(go.Candlestick(
        x=df_plot["time"],
        open=df_plot["open"],
        high=df_plot["high"],
        low=df_plot["low"],
        close=df_plot["close"],
        name="US30 M5",
        increasing_line_color="#00d4aa",
        decreasing_line_color="#ff4444",
        showlegend=False,
    ), row=5, col=1)

    # OBs en ese rango
    obs_plot = obs[
        (obs["confirmed_at"] >= cutoff) |
        (obs["entry_time"] >= cutoff)
    ].copy()

    for _, ob in obs_plot.iterrows():
        color = "rgba(0,212,170,0.12)" if ob["ob_type"] == "bullish" else "rgba(255,68,68,0.12)"
        border = "rgba(0,212,170,0.5)" if ob["ob_type"] == "bullish" else "rgba(255,68,68,0.5)"
        x0 = ob["confirmed_at"]
        x1 = ob["exit_time"] if pd.notna(ob["exit_time"]) else df_plot["time"].max()

        fig.add_shape(
            type="rect",
            x0=x0, x1=x1,
            y0=ob["zone_low"], y1=ob["zone_high"],
            fillcolor=color,
            line=dict(color=border, width=0.5),
            row=5, col=1,
        )

    # Trades en ese rango
    trades_plot = trades[trades["entry_time"] >= cutoff]

    longs  = trades_plot[trades_plot["tipo"] == "LONG"]
    shorts = trades_plot[trades_plot["tipo"] == "SHORT"]

    for label, df_t, symbol, color in [
        ("LONG entry", longs, "triangle-up", "#00d4aa"),
        ("SHORT entry", shorts, "triangle-down", "#ff4444"),
    ]:
        fig.add_trace(go.Scatter(
            x=df_t["entry_time"],
            y=df_t["entry_price"],
            mode="markers",
            name=label,
            marker=dict(symbol=symbol, size=8, color=color),
            hovertemplate="<b>%{text}</b><br>Entry: %{y:.1f}<br>PnL: $%{customdata:.2f}<extra></extra>",
            text=df_t["tipo"],
            customdata=df_t["pnl_usd"],
        ), row=5, col=1)

    fig.update_xaxes(
        rangeslider_visible=False,
        rangeselector=dict(
            buttons=[
                dict(count=3, label="3d", step="day", stepmode="backward"),
                dict(count=7, label="7d", step="day", stepmode="backward"),
                dict(count=14, label="14d", step="day", stepmode="backward"),
                dict(step="all", label="Todo"),
            ]
        ),
        row=5, col=1,
    )

# ----------------------------------------------------------------
# Layout global
# ----------------------------------------------------------------
fig.update_layout(
    title=dict(
        text="<b>Bot 2 London — US30.cash — Backtest 518 dias</b><br>"
             f"<span style='font-size:13px;color:#aaa'>RR=2.5 | Buffer=35 | Sesion 10:00-19:00 UTC+2 | "
             f"WR={wr:.1f}% | PF={pf:.2f} | Retorno={ret_pct:+.1f}% | DD={max_dd:.1f}%</span>",
        font=dict(size=18, color="white"),
        x=0.5,
    ),
    paper_bgcolor="#0d0f1a",
    plot_bgcolor="#13151f",
    font=dict(color="#cccccc", size=11),
    height=350 * n_panels,
    showlegend=True,
    legend=dict(
        bgcolor="rgba(20,22,35,0.8)",
        bordercolor="#333",
        borderwidth=1,
    ),
    barmode="overlay",
)

# Ejes
for i in range(1, n_panels + 1):
    fig.update_xaxes(gridcolor="#1e2130", row=i, col=1)
    fig.update_yaxes(gridcolor="#1e2130", row=i, col=1)

fig.update_yaxes(title_text="Balance ($)", row=1, col=1)
fig.update_yaxes(title_text="N Trades", row=2, col=1)
fig.update_xaxes(title_text="PnL por trade ($)", row=2, col=1)

# ----------------------------------------------------------------
# Exportar HTML autocontenido
# ----------------------------------------------------------------
print(f"\nExportando HTML...")
pio.write_html(
    fig,
    file=str(OUT_FILE),
    include_plotlyjs=True,
    full_html=True,
    auto_open=False,
)
size_mb = OUT_FILE.stat().st_size / 1024 / 1024
print(f"  Archivo: {OUT_FILE}")
print(f"  Tamano:  {size_mb:.1f} MB")
print(f"\nAbrir en browser: {OUT_FILE.resolve()}")
