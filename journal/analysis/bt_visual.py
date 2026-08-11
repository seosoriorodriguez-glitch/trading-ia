# -*- coding: utf-8 -*-
"""
Corre la estrategia STOP (=live) sobre CSVs arbitrarios (M5/M1), imprime el listado
de trades y VUELCA un JSON (velas M5 + zonas OB + trades) para dibujar el grafico.
Uso: python bt_visual.py <m5.csv> <m1.csv> <us30|oro|dax> <out.json> [dec]
"""
import sys, json, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.ob_detection import detect_order_blocks
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from strategies.order_block_gold.backtest.config import GOLD_PARAMS
from strategies.order_block_dax.backtest.config import DAX_PARAMS
from strategies.order_block_london.backtest.config import LONDON_PARAMS

m5f, m1f, cfg, outp = sys.argv[1], sys.argv[2], sys.argv[3].lower(), sys.argv[4]
dec = int(sys.argv[5]) if len(sys.argv) > 5 else 1
params = {"us30": LONDON_PARAMS, "oro": GOLD_PARAMS, "dax": DAX_PARAMS}[cfg]
name = {"us30": "US30 London", "oro": "ORO", "dax": "DAX"}[cfg]

df5 = load_csv(m5f); df1 = load_csv(m1f)
p = copy.deepcopy(params)
obs = detect_order_blocks(df5, p)
res = OrderBlockBacktesterLimitOrders(copy.deepcopy(p)).run(df5, df1)

# --- listado ---
print(f"\n{'='*90}")
print(f" {name} — STOP (=live) — {df1.time.iloc[0]} -> {df1.time.iloc[-1]}  buffer {p['buffer_points']} RR {p['target_rr']}")
print(f" OBs detectados: {len(obs)} | sesion: {list(p['sessions'].keys())}")
print(f"{'='*90}")
fmt = f"%.{dec}f"
if res is None or res.empty:
    print("  SIN OPERACIONES en la ventana (normal si es corta / fuera de sesion).")
    trades = []
else:
    res = res.sort_values("entry_time").reset_index(drop=True)
    print(f" {'#':>2} {'entrada':<16} {'dir':<5} {'entry':>10} {'SL':>10} {'TP':>10} {'salida':<16} {'mot':<4} {'R':>6} res")
    for i, r in res.iterrows():
        w = r.pnl_r > 0
        print(f" {i+1:>2} {pd.Timestamp(r.entry_time):%m-%d %H:%M}    {r.direction:<5} {fmt%r.entry_price:>10} "
              f"{fmt%r.sl:>10} {fmt%r.tp:>10} {pd.Timestamp(r.exit_time):%m-%d %H:%M}    {r.exit_reason:<4} "
              f"{r.pnl_r:>+6.2f} {'GANA' if w else 'PIERDE'}")
    n = len(res); ww = int((res.pnl_r > 0).sum())
    print(f" TOTAL {n} | {ww} ganan / {n-ww} pierden | SumaR {res.pnl_r.sum():+.2f}")
    trades = [{"entry_time": str(r.entry_time), "dir": r.direction, "entry": float(r.entry_price),
               "sl": float(r.sl), "tp": float(r.tp), "exit_time": str(r.exit_time),
               "reason": r.exit_reason, "r": float(r.pnl_r)} for _, r in res.iterrows()]

# --- JSON para grafico ---
data = {
    "name": name, "dec": dec,
    "candles": [{"t": str(r.time), "o": float(r.open), "h": float(r.high), "l": float(r.low), "c": float(r.close)}
                for _, r in df5.iterrows()],
    "zones": [{"type": o.ob_type, "conf": str(o.confirmed_at), "high": float(o.zone_high),
               "low": float(o.zone_low), "status": str(getattr(o.status, "name", o.status))} for o in obs],
    "trades": trades,
}
Path(outp).write_text(json.dumps(data), encoding="utf-8")
print(f" JSON -> {outp}  ({len(data['candles'])} velas, {len(data['zones'])} zonas, {len(trades)} trades)")
