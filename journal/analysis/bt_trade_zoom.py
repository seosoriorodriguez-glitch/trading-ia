# -*- coding: utf-8 -*-
"""
Grafica UNA operacion (por defecto una ganadora clara) con zoom: ventana de velas M5
alrededor del trade + su zona OB + entrada/SL/TP. Uso:
  python bt_trade_zoom.py <m5> <m1> <us30|oro|dax> <out.json> [win|lose] [dec] [buffer]
"""
import sys, json, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from strategies.order_block_gold.backtest.config import GOLD_PARAMS
from strategies.order_block_dax.backtest.config import DAX_PARAMS
from strategies.order_block_london.backtest.config import LONDON_PARAMS

m5f, m1f, cfg, outp = sys.argv[1], sys.argv[2], sys.argv[3].lower(), sys.argv[4]
want = sys.argv[5] if len(sys.argv) > 5 else "win"
dec = int(sys.argv[6]) if len(sys.argv) > 6 else 2
params = {"us30": LONDON_PARAMS, "oro": GOLD_PARAMS, "dax": DAX_PARAMS}[cfg]
name = {"us30": "US30 London", "oro": "ORO", "dax": "DAX"}[cfg]

df5 = load_csv(m5f); df1 = load_csv(m1f)
df5 = df5[(df5.time >= df1.time.iloc[0]) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)
p = copy.deepcopy(params)
if len(sys.argv) > 7: p["buffer_points"] = float(sys.argv[7])
res = OrderBlockBacktesterLimitOrders(copy.deepcopy(p)).run(df5, df1)
res = res.sort_values("entry_time").reset_index(drop=True)
res["dur"] = (pd.to_datetime(res.exit_time) - pd.to_datetime(res.entry_time)).dt.total_seconds() / 60

# elegir el trade: ganador (tp) con duracion 40-240min, el de mayor recorrido
cand = res[(res.pnl_r > 0) & (res.exit_reason == "tp") & (res.dur.between(40, 240))] if want == "win" \
    else res[res.pnl_r <= 0]
if cand.empty: cand = res[res.pnl_r > 0] if want == "win" else res[res.pnl_r <= 0]
t = cand.iloc[len(cand) // 2]   # uno del medio, representativo

etime, xtime = pd.Timestamp(t.entry_time), pd.Timestamp(t.exit_time)
lo_t = etime - pd.Timedelta(hours=4); hi_t = xtime + pd.Timedelta(hours=1)
win = df5[(df5.time >= lo_t) & (df5.time <= hi_t)]

data = {
    "name": f"{name} — operación GANADORA (+{t.pnl_r:.2f}R)" if t.pnl_r > 0 else f"{name} — operación perdedora ({t.pnl_r:.2f}R)",
    "dec": dec,
    "candles": [{"t": str(r.time), "o": float(r.open), "h": float(r.high), "l": float(r.low), "c": float(r.close)} for _, r in win.iterrows()],
    "zones": [{"type": "bullish" if t.direction == "long" else "bearish", "conf": str(t.ob_confirmed_at),
               "high": float(t.ob_zone_high), "low": float(t.ob_zone_low), "status": "traded"}],
    "trades": [{"entry_time": str(t.entry_time), "dir": t.direction, "entry": float(t.entry_price),
                "sl": float(t.sl), "tp": float(t.tp), "exit_time": str(t.exit_time),
                "reason": t.exit_reason, "r": float(t.pnl_r)}],
}
Path(outp).write_text(json.dumps(data), encoding="utf-8")
print(f"Trade elegido: {t.direction} {etime:%m-%d %H:%M} -> {xtime:%m-%d %H:%M} ({t.dur:.0f}min) "
      f"entry {t.entry_price:.2f} SL {t.sl:.2f} TP {t.tp:.2f} = {t.pnl_r:+.2f}R")
print(f"Zona OB: {t.ob_zone_low:.2f}-{t.ob_zone_high:.2f} conf {pd.Timestamp(t.ob_confirmed_at):%m-%d %H:%M}")
print(f"JSON -> {outp} ({len(data['candles'])} velas)")
