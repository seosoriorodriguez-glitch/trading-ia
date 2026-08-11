# -*- coding: utf-8 -*-
"""
Persistencia LOCAL del historial de backtests (SQLite + CSV por run). Sin dependencias extra.
- metadata + metricas + notas -> dashboard/runs.db (tabla `runs`)
- trades de cada run -> dashboard/runs/<id>.csv (para recarga instantanea del grafico)
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd

DASH = Path(__file__).resolve().parent
DB = DASH / "runs.db"
RUNS_DIR = DASH / "runs"

_COLS = ["id", "created_at", "asset", "session", "rr", "spread", "risk_pct",
         "n_trades", "wr", "pf", "pf_1h", "pf_2h", "robust",
         "return_pct", "dd_pct", "sumR", "days", "notes", "config_json"]


def init_db():
    RUNS_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT, asset TEXT, session TEXT, rr REAL, spread REAL, risk_pct REAL,
            n_trades INTEGER, wr REAL, pf REAL, pf_1h REAL, pf_2h REAL, robust INTEGER,
            return_pct REAL, dd_pct REAL, sumR REAL, days INTEGER,
            notes TEXT, config_json TEXT
        )""")
    con.commit()
    con.close()


def save_run(config, metrics, results_df, notes=""):
    init_db()
    con = sqlite3.connect(DB)
    cur = con.execute(
        """INSERT INTO runs (created_at,asset,session,rr,spread,risk_pct,n_trades,wr,pf,
           pf_1h,pf_2h,robust,return_pct,dd_pct,sumR,days,notes,config_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (datetime.now().isoformat(timespec="seconds"),
         config["asset"], config["session"], config["rr"], config["spread"], config["risk_pct"],
         metrics["n_trades"], metrics["wr"], metrics["pf"], metrics["pf_1h"], metrics["pf_2h"],
         int(bool(metrics["robust"])), metrics["return_pct"], metrics["dd_pct"], metrics["sumR"],
         metrics["days"], notes or "", json.dumps(config)))
    run_id = cur.lastrowid
    con.commit()
    con.close()
    if results_df is not None and not results_df.empty:
        results_df.to_csv(RUNS_DIR / f"{run_id}.csv", index=False)
    return run_id


def list_runs():
    init_db()
    con = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM runs ORDER BY id DESC", con)
    con.close()
    return df


def get_run(run_id):
    init_db()
    con = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM runs WHERE id=?", con, params=(int(run_id),))
    con.close()
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    row["config"] = json.loads(row["config_json"])
    csv = RUNS_DIR / f"{run_id}.csv"
    if csv.exists():
        res = pd.read_csv(csv)
        for c in ("entry_time", "exit_time", "ob_confirmed_at"):
            if c in res.columns:
                res[c] = pd.to_datetime(res[c], errors="coerce")
        row["results"] = res
    else:
        row["results"] = None
    return row


def delete_run(run_id):
    init_db()
    con = sqlite3.connect(DB)
    con.execute("DELETE FROM runs WHERE id=?", (int(run_id),))
    con.commit()
    con.close()
    csv = RUNS_DIR / f"{run_id}.csv"
    if csv.exists():
        csv.unlink()
