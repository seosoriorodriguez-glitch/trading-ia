# -*- coding: utf-8 -*-
"""
Iteracion RAPIDA del FVG sobre los ultimos N dias (para tweak veloz).
Comportamiento natural del live: max_active_fvgs=3, sin cap, se mitigan solas.
Cambia los PARAMS de arriba y re-corre.
"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
from strategies.fair_value_gap.backtest.config import US30_PARAMS
from strategies.fair_value_gap.backtest.data_loader import load_csv
from strategies.fair_value_gap.backtest.backtester import FVGBacktester

# ---------------- PARAMS PARA TWEAK ----------------
DIAS          = 40
MIN_ZONE      = 5
TARGET_RR     = 2.0
BUFFER        = 25
MAX_ACTIVE    = 3      # ultimas 3 zonas (como el live)
MAX_SIM       = 3      # hasta 3 abiertas (natural, se mitigan)
SPREAD        = 4      # costo real medido
ENTRY         = "conservative"   # "conservative" (STOP) o "aggressive" (toque)
RISK_PCT      = 0.005
# ---------------------------------------------------

print(f"Cargando y recortando ultimos {DIAS} dias...", flush=True)
dfh = load_csv("data/US30_icm_M5_518d.csv")
dfl = load_csv("data/US30_icm_M1_500k.csv")
cutoff = dfl["time"].iloc[-1] - pd.Timedelta(days=DIAS)
dfh = dfh[dfh.time >= cutoff].reset_index(drop=True)
dfl = dfl[dfl.time >= cutoff].reset_index(drop=True)
print(f"  M5: {len(dfh):,}  M1: {len(dfl):,}  ({dfl.time.iloc[0]} -> {dfl.time.iloc[-1]})", flush=True)

p = copy.deepcopy(US30_PARAMS)
p.update({
    "min_zone_points": MIN_ZONE, "target_rr": TARGET_RR, "buffer_points": BUFFER,
    "max_active_fvgs": MAX_ACTIVE, "max_simultaneous_trades": MAX_SIM,
    "avg_spread_points": SPREAD, "entry_method": ENTRY, "risk_per_trade_pct": RISK_PCT,
    "close_before_weekend": True, "weekend_close_hour": 19,
})

bt = FVGBacktester(p)
df = bt.run(dfh, dfl)
if df.empty:
    print("Sin trades."); sys.exit()

wins = df[df.pnl_usd > 0]; n = len(df); wr = len(wins) / n * 100
gl = abs(df[df.pnl_usd <= 0].pnl_usd.sum()); pf = wins.pnl_usd.sum() / gl if gl > 0 else 99
sumr = df.pnl_r.sum()
longs = df[df.direction == "long"]; shorts = df[df.direction == "short"]

print("\n" + "=" * 56)
print(f"  FVG RAPIDO — {DIAS}d | zona>={MIN_ZONE} RR={TARGET_RR} buf={BUFFER} "
      f"maxsim={MAX_SIM} entry={ENTRY}")
print("=" * 56)
print(f"  Trades: {n}  ({n/DIAS:.1f}/dia)")
print(f"  Win Rate: {wr:.1f}%   Profit Factor: {pf:.2f}")
print(f"  Suma R: {sumr:+.1f}R   Avg R: {df.pnl_r.mean():+.3f}")
print(f"  LONG:  {len(longs):3d}  WR {(longs.pnl_usd>0).mean()*100 if len(longs) else 0:.0f}%  "
      f"SumaR {longs.pnl_r.sum():+.0f}")
print(f"  SHORT: {len(shorts):3d}  WR {(shorts.pnl_usd>0).mean()*100 if len(shorts) else 0:.0f}%  "
      f"SumaR {shorts.pnl_r.sum():+.0f}")
print("=" * 56)
