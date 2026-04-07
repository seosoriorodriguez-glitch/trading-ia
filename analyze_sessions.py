import pandas as pd

df = pd.read_csv("strategies/fair_value_gap/backtest/results/fvg_live_exact.csv")
df["zone_size"] = df["fvg_zone_high"] - df["fvg_zone_low"]
RISK = 50.0

for sess in ["asia", "london", "new_york"]:
    s = df[df["session"] == sess]
    if len(s) == 0:
        continue
    wr = (s["exit_reason"] == "tp").sum() / len(s) * 100
    pnl = s["pnl_r"].sum() * RISK
    gw = s[s["pnl_r"] > 0]["pnl_r"].sum() * RISK
    gl = abs(s[s["pnl_r"] <= 0]["pnl_r"].sum()) * RISK
    pf = gw / gl if gl > 0 else float("inf")
    print(f"\n{sess.upper():12s}: {len(s)} trades | WR {wr:.1f}% | PF {pf:.2f} | PnL ${pnl:+,.0f}")
    print(f"  zone: mean={s.zone_size.mean():.1f} median={s.zone_size.median():.1f} min={s.zone_size.min():.1f}")
    print(f"  zones < 1pt: {(s.zone_size < 1).sum()} | <5pt: {(s.zone_size < 5).sum()} | <10pt: {(s.zone_size < 10).sum()}")

    # WR by zone size
    for mn, mx in [(0, 5), (5, 10), (10, 20), (20, 50), (50, 999)]:
        sub = s[(s.zone_size >= mn) & (s.zone_size < mx)]
        if len(sub) < 10:
            continue
        sub_wr = (sub["exit_reason"] == "tp").sum() / len(sub) * 100
        sub_pnl = sub["pnl_r"].sum() * RISK
        print(f"    zone [{mn:3d}-{mx:3d}): {len(sub):4d} trades | WR {sub_wr:.1f}% | PnL ${sub_pnl:+,.0f}")

# Overall: FVG without asia
print("\n" + "="*60)
print("SIN ASIA (solo london + ny):")
no_asia = df[df["session"] != "asia"]
wr2 = (no_asia["exit_reason"] == "tp").sum() / len(no_asia) * 100
pnl2 = no_asia["pnl_r"].sum() * RISK
gw2 = no_asia[no_asia["pnl_r"] > 0]["pnl_r"].sum() * RISK
gl2 = abs(no_asia[no_asia["pnl_r"] <= 0]["pnl_r"].sum()) * RISK
pf2 = gw2 / gl2 if gl2 > 0 else float("inf")
print(f"  {len(no_asia)} trades | WR {wr2:.1f}% | PF {pf2:.2f} | PnL ${pnl2:+,.0f}")

# Without micro zones
print("\nSIN ZONAS < 5pts (todas las sesiones):")
big = df[df["zone_size"] >= 5]
wr3 = (big["exit_reason"] == "tp").sum() / len(big) * 100
pnl3 = big["pnl_r"].sum() * RISK
gw3 = big[big["pnl_r"] > 0]["pnl_r"].sum() * RISK
gl3 = abs(big[big["pnl_r"] <= 0]["pnl_r"].sum()) * RISK
pf3 = gw3 / gl3 if gl3 > 0 else float("inf")
print(f"  {len(big)} trades | WR {wr3:.1f}% | PF {pf3:.2f} | PnL ${pnl3:+,.0f}")

# Without micro zones AND without asia
print("\nSIN ZONAS < 5pts Y SIN ASIA:")
strict = df[(df["zone_size"] >= 5) & (df["session"] != "asia")]
wr4 = (strict["exit_reason"] == "tp").sum() / len(strict) * 100
pnl4 = strict["pnl_r"].sum() * RISK
gw4 = strict[strict["pnl_r"] > 0]["pnl_r"].sum() * RISK
gl4 = abs(strict[strict["pnl_r"] <= 0]["pnl_r"].sum()) * RISK
pf4 = gw4 / gl4 if gl4 > 0 else float("inf")
print(f"  {len(strict)} trades | WR {wr4:.1f}% | PF {pf4:.2f} | PnL ${pnl4:+,.0f}")
