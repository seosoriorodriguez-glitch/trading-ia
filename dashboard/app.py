# -*- coding: utf-8 -*-
"""
Dashboard interno de backtests Order Block (Streamlit). Uso personal, 100% aditivo.
Correr:  streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd
import streamlit as st

import backtest_runner as runner
import charts
import storage

st.set_page_config(page_title="OB Backtest Dashboard", layout="wide")
st.title("📊 Order Block — Backtest Dashboard")
st.caption("Interno · motor real M5+M1 · 100% aditivo (no toca producción)")


def _metric_row(m):
    c = st.columns(6)
    c[0].metric("Trades", m["n_trades"])
    c[1].metric("Win Rate", f"{m['wr']}%")
    c[2].metric("Profit Factor", m["pf"])
    c[3].metric("Retorno", f"{m['return_pct']}%")
    c[4].metric("Max DD", f"{m['dd_pct']}%")
    c[5].metric("Robusta", "✅ SÍ" if m["robust"] else "❌ NO")
    st.caption(
        f"PF 1ª mitad {m['pf_1h']} / 2ª {m['pf_2h']}  ·  {m['trades_month']}/mes  ·  "
        f"~{m['annual_pct']:.0f}%/año  ·  {m['days']}d  ·  rango M5 med {m['med']}")


# ---------------- Sidebar: correr con botones ----------------
with st.sidebar:
    st.header("Parámetros")
    assets = runner.list_assets()
    if not assets:
        st.error("No hay pares M5+M1 en data/. Descarga datos primero.")
        st.stop()
    default_idx = assets.index("US30") if "US30" in assets else 0
    asset = st.selectbox("Activo", assets, index=default_idx)
    session = st.selectbox("Sesión", ["london", "ny", "both", "24_7"], index=2)
    rr = st.number_input("RR (target)", 0.5, 10.0, 2.5, 0.5)
    spread = st.number_input("Costo / spread (pts precio)", 0.0, 1000.0,
                             float(runner.default_spread(asset)), format="%.5f")
    risk = st.number_input("Riesgo % por trade", 0.05, 2.0, 0.5, 0.05) / 100.0
    run_btn = st.button("▶ Correr backtest", type="primary", width="stretch")

tab_run, tab_hist = st.tabs(["🔬 Backtest", "🗂️ Historial"])

# ==================== TAB BACKTEST ====================
with tab_run:
    if run_btn:
        with st.spinner("Corriendo motor real M5+M1…"):
            try:
                st.session_state["result"] = runner.run_backtest(asset, session, spread, rr, risk)
            except Exception as e:
                st.session_state["result"] = None
                st.exception(e)

    result = st.session_state.get("result")
    if result is None:
        st.info("Elige parámetros en la barra lateral y pulsa **Correr backtest**.")
    elif result["results"] is None or result["results"].empty:
        st.warning("SIN TRADES para esa configuración.")
        _metric_row(result["metrics"])
    else:
        cfg = result["config"]
        st.subheader(f"{cfg['asset']} · {cfg['session']} · RR {cfg['rr']} · costo {cfg['spread']} · riesgo {cfg['risk_pct']*100:.2f}%")
        _metric_row(result["metrics"])

        st.markdown("##### Curva de equity")
        st.plotly_chart(charts.equity_curve(result["results"]), width="stretch")

        st.markdown("##### Gráfico — velas · zonas OB · trades")
        res = result["results"]
        opts = ["(últimas velas)"] + [
            f"#{int(t.trade_id)} {t.direction} {t.entry_time} {t.pnl_r:+.2f}R"
            for _, t in res.sort_values("entry_time").iterrows()
        ]
        pick = st.selectbox("Enfocar un trade (zoom a su zona)", opts, index=0)
        focus = None
        if pick != "(últimas velas)":
            tid = int(pick.split()[0].lstrip("#"))
            focus = pd.to_datetime(res.loc[res.trade_id == tid, "entry_time"].iloc[0])
        st.plotly_chart(
            charts.candles_zones_trades(result["df5"], result["zones"], res, focus_time=focus),
            width="stretch")

        with st.expander("📋 Tabla de trades"):
            st.dataframe(res, width="stretch", height=300)

        st.markdown("##### Guardar este run")
        notes = st.text_area("Notas / análisis", key="notes_run",
                             placeholder="Ej: NY rinde mejor que London aquí; DD alto en el 2º trimestre…")
        if st.button("💾 Guardar en historial"):
            rid = storage.save_run(cfg, result["metrics"], res, notes)
            st.success(f"Guardado run #{rid}")

# ==================== TAB HISTORIAL ====================
with tab_hist:
    runs = storage.list_runs()
    if runs.empty:
        st.info("Aún no hay runs guardados. Corre uno y pulsa **Guardar en historial**.")
    else:
        show = runs[["id", "created_at", "asset", "session", "rr", "spread", "risk_pct",
                     "n_trades", "wr", "pf", "return_pct", "dd_pct", "robust", "notes"]].copy()
        show["robust"] = show["robust"].map({1: "✅", 0: "❌"})
        st.markdown("##### Todos los runs")
        st.dataframe(show, width="stretch", height=260)

        ids = runs["id"].tolist()

        st.markdown("##### Ver un run")
        sel = st.selectbox("Run", ids, format_func=lambda i: f"#{i} · {runs.loc[runs.id==i,'asset'].iloc[0]} · {runs.loc[runs.id==i,'session'].iloc[0]}")
        run = storage.get_run(sel)
        if run:
            m = {"n_trades": run["n_trades"], "wr": run["wr"], "pf": run["pf"],
                 "return_pct": run["return_pct"], "dd_pct": run["dd_pct"], "robust": run["robust"],
                 "pf_1h": run["pf_1h"], "pf_2h": run["pf_2h"], "trades_month": "-",
                 "annual_pct": 0, "days": run["days"], "med": "-"}
            _metric_row(m)
            if run["notes"]:
                st.info(f"📝 {run['notes']}")
            if run["results"] is not None and not run["results"].empty:
                st.plotly_chart(charts.equity_curve(run["results"]), width="stretch")
                with st.spinner("Reconstruyendo gráfico…"):
                    cd = runner.chart_data(run["config"])
                st.plotly_chart(
                    charts.candles_zones_trades(cd["df5"], cd["zones"], run["results"]),
                    width="stretch")
            c1, _ = st.columns([1, 5])
            if c1.button("🗑️ Borrar run"):
                storage.delete_run(sel)
                st.rerun()

        st.markdown("---")
        st.markdown("##### Comparar A vs B")
        cc = st.columns(2)
        a = cc[0].selectbox("Run A", ids, key="cmp_a")
        b = cc[1].selectbox("Run B", ids, key="cmp_b", index=min(1, len(ids)-1))
        ra, rb = storage.get_run(a), storage.get_run(b)
        if ra and rb:
            comp = pd.DataFrame([
                {"run": f"#{a} {ra['asset']}/{ra['session']}", "PF": ra["pf"], "WR": ra["wr"],
                 "Retorno%": ra["return_pct"], "DD%": ra["dd_pct"], "Trades": ra["n_trades"],
                 "Robusta": "✅" if ra["robust"] else "❌"},
                {"run": f"#{b} {rb['asset']}/{rb['session']}", "PF": rb["pf"], "WR": rb["wr"],
                 "Retorno%": rb["return_pct"], "DD%": rb["dd_pct"], "Trades": rb["n_trades"],
                 "Robusta": "✅" if rb["robust"] else "❌"},
            ])
            st.dataframe(comp, width="stretch", hide_index=True)
            st.plotly_chart(
                charts.equity_overlay([
                    (f"#{a} {ra['asset']}/{ra['session']}", ra["results"]),
                    (f"#{b} {rb['asset']}/{rb['session']}", rb["results"]),
                ]), width="stretch")
