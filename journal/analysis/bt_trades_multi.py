# -*- coding: utf-8 -*-
"""
Selecciona N trades REPARTIDOS parejo en la muestra (sin cherry-pick) y arma un JSON
multi-panel (cada trade = velas M5 + su zona OB + entrada/SL/TP) para validar sesgo.
Uso: python bt_trades_multi.py <m5> <m1> <us30|oro|dax> <london|both> <N> <out.json> [dec]
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

m5f, m1f, cfg, ses, N, outp = sys.argv[1], sys.argv[2], sys.argv[3].lower(), sys.argv[4], int(sys.argv[5]), sys.argv[6]
dec = int(sys.argv[7]) if len(sys.argv) > 7 else 1
PARAMS = {"us30": LONDON_PARAMS, "oro": GOLD_PARAMS, "dax": DAX_PARAMS}[cfg]
NAME = {"us30": "US30 London", "oro": "ORO", "dax": "DAX London"}[cfg]
SES = {"london": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15}},
       "both": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15},
                "new_york": {"start": "13:30", "end": "23:00", "skip_minutes": 15}}}

df5 = load_csv(m5f); df1 = load_csv(m1f)
df5 = df5[(df5.time >= df1.time.iloc[0]) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)
p = copy.deepcopy(PARAMS); p["sessions"] = SES[ses]
res = OrderBlockBacktesterLimitOrders(p).run(df5, df1)
res = res.sort_values("entry_time").reset_index(drop=True)
n = len(res)

# seleccion determinística: N indices repartidos parejo en toda la muestra
idxs = sorted(set(round(i*(n-1)/(N-1)) for i in range(N)))
sel = res.iloc[idxs].reset_index(drop=True)

wins = int((sel.pnl_r > 0).sum())
print(f"=== {NAME} — {len(sel)} trades repartidos (de {n} totales) | {wins} ganan / {len(sel)-wins} pierden ===")
fmt = f"%.{dec}f"
panels = []
for _, t in sel.iterrows():
    et, xt = pd.Timestamp(t.entry_time), pd.Timestamp(t.exit_time)
    win = df5[(df5.time >= et - pd.Timedelta(hours=3)) & (df5.time <= xt + pd.Timedelta(hours=1.5))]
    print(f"  {et:%m-%d %H:%M} {t.direction:<5} entry {fmt%t.entry_price} SL {fmt%t.sl} TP {fmt%t.tp} "
          f"-> {xt:%m-%d %H:%M} {t.exit_reason} {t.pnl_r:+.2f}R {'GANA' if t.pnl_r>0 else 'PIERDE'}")
    panels.append({
        "candles": [{"t": str(r.time), "o": float(r.open), "h": float(r.high), "l": float(r.low), "c": float(r.close)} for _, r in win.iterrows()],
        "zone": {"type": "bullish" if t.direction == "long" else "bearish", "conf": str(t.ob_confirmed_at),
                 "high": float(t.ob_zone_high), "low": float(t.ob_zone_low)},
        "trade": {"entry_time": str(t.entry_time), "dir": t.direction, "entry": float(t.entry_price),
                  "sl": float(t.sl), "tp": float(t.tp), "exit_time": str(t.exit_time),
                  "reason": t.exit_reason, "r": float(t.pnl_r)},
    })
data = {"name": NAME, "dec": dec, "wins": wins, "losses": len(sel) - wins, "total": n, "panels": panels}
Path(outp).write_text(json.dumps(data), encoding="utf-8")
print(f" JSON -> {outp} ({len(panels)} paneles)")
