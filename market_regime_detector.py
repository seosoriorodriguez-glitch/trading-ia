# -*- coding: utf-8 -*-
"""
Market Regime Detector - Deteccion de regimenes de mercado via K-Means clustering.

Uso: solo analisis POST-backtest. No modifica ningun bot en produccion.
Los regimenes se calculan con datos estrictamente pasados (anti-look-ahead).

Regimenes tipicos que suele encontrar:
  0 - Trending limpio     : alta pendiente SMA, estructura HH/LL clara
  1 - Rango comprimido    : ATR bajo, sin estructura, choppy
  2 - Alta volatilidad    : ATR expandido, movimientos bruscos, noticias
"""

import pandas as pd
import numpy as np
import warnings
from typing import Tuple, Optional

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False
    print("AVISO: scikit-learn no instalado. Correr: pip install scikit-learn")

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import seaborn as sns
    PLOT_OK = True
except ImportError:
    PLOT_OK = False


# --------------------------------------------------------------------------
# 1. Calculo de features
# --------------------------------------------------------------------------

def calculate_regime_features(df: pd.DataFrame, lookback: int = 50,
                               ma_period: int = 20, atr_period: int = 14) -> pd.DataFrame:
    """
    Calcula features de mercado usando SOLO datos pasados (anti-look-ahead).
    Usa shift(1) para asegurar que cada vela no se incluye en su propio calculo.

    Features:
      atr_norm         : ATR / precio — volatilidad relativa
      range_ratio      : rango N velas / ATR — compresion vs expansion
      ma_slope         : pendiente SMA(20) normalizada — tendencia
      body_ratio_avg   : avg(cuerpo/rango) — decision vs indecision
      higher_highs_r   : % velas con higher high — estructura alcista
      lower_lows_r     : % velas con lower low — estructura bajista
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])

    # --- ATR clasico ---
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["_atr"] = tr.rolling(atr_period, min_periods=1).mean()

    # --- SMA ---
    df["_sma"] = df["close"].rolling(ma_period, min_periods=1).mean()

    # --- Features rolling (shift(1): excluye vela actual) ---
    # atr_norm: ATR relativo al precio
    df["atr_norm"] = (df["_atr"] / df["close"]).shift(1).rolling(lookback, min_periods=lookback//2).mean()

    # range_ratio: rango de ventana / ATR
    rolling_range = (df["high"].rolling(lookback, min_periods=lookback//2).max()
                   - df["low"].rolling(lookback, min_periods=lookback//2).min()).shift(1)
    df["range_ratio"] = rolling_range / df["_atr"].shift(1).replace(0, np.nan)

    # ma_slope: pendiente SMA normalizada
    sma_prev = df["_sma"].shift(lookback)
    df["ma_slope"] = ((df["_sma"].shift(1) - sma_prev) / sma_prev.replace(0, np.nan))

    # body_ratio_avg: cuerpo/rango promedio en ventana
    body  = (df["close"] - df["open"]).abs()
    range_= (df["high"]  - df["low"]).replace(0, np.nan)
    df["body_ratio_avg"] = (body / range_).shift(1).rolling(lookback, min_periods=lookback//2).mean()

    # higher_highs_ratio: % velas con higher high
    hh = (df["high"] > df["high"].shift(1)).astype(float)
    df["higher_highs_r"] = hh.shift(1).rolling(lookback, min_periods=lookback//2).mean()

    # lower_lows_ratio: % velas con lower low
    ll = (df["low"] < df["low"].shift(1)).astype(float)
    df["lower_lows_r"] = ll.shift(1).rolling(lookback, min_periods=lookback//2).mean()

    # Limpiar columnas auxiliares
    df.drop(columns=["_atr", "_sma"], inplace=True)

    n_nan = df[["atr_norm","range_ratio","ma_slope","body_ratio_avg",
                "higher_highs_r","lower_lows_r"]].isna().any(axis=1).sum()
    if n_nan > 0:
        print(f"  Features: {n_nan} filas descartadas por lookback insuficiente")

    return df


FEATURE_COLS = ["atr_norm", "range_ratio", "ma_slope",
                "body_ratio_avg", "higher_highs_r", "lower_lows_r"]


# --------------------------------------------------------------------------
# 2. Entrenar modelo
# --------------------------------------------------------------------------

def fit_regime_model(df_train: pd.DataFrame, n_clusters: int = 3) -> Tuple:
    """
    Entrena KMeans sobre df_train (sin NaN en features).
    Retorna (model, scaler) fiteados solo en train.
    """
    assert SKLEARN_OK, "scikit-learn requerido"

    X = df_train[FEATURE_COLS].dropna()
    print(f"  Training con {len(X)} velas, {n_clusters} clusters")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    model.fit(X_scaled)

    labels = model.labels_
    if len(set(labels)) > 1:
        sil = silhouette_score(X_scaled, labels)
        print(f"  Silhouette score: {sil:.3f}  (>0.3 es aceptable, >0.5 es bueno)")

    return model, scaler


# --------------------------------------------------------------------------
# 3. Predecir regimenes
# --------------------------------------------------------------------------

def predict_regimes(df: pd.DataFrame, model, scaler) -> pd.DataFrame:
    """
    Aplica el modelo a todo el DataFrame (train + test).
    Agrega columna 'regime'. Filas con NaN quedan como -1.
    """
    df = df.copy()
    valid_mask = df[FEATURE_COLS].notna().all(axis=1)
    X = df.loc[valid_mask, FEATURE_COLS]
    X_scaled = scaler.transform(X)
    df.loc[valid_mask, "regime"] = model.predict(X_scaled).astype(int)
    df["regime"] = df["regime"].fillna(-1).astype(int)
    return df


# --------------------------------------------------------------------------
# 4. Analisis regimen vs performance
# --------------------------------------------------------------------------

def analyze_regime_performance(trades_df: pd.DataFrame,
                                regimes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza cada trade con el regimen de su vela de ENTRADA.
    Muestra: trades, WR, PF, avg R, avg PnL por regimen.
    """
    regimes_df = regimes_df.copy()
    regimes_df["time"] = pd.to_datetime(regimes_df["time"])
    regimes_df = regimes_df.set_index("time")["regime"]

    trades = trades_df.copy()
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])

    # Asignar regimen por merge_asof (toma la vela M5 mas cercana anterior)
    regime_df = regimes_df.reset_index().rename(columns={"time": "entry_time", "regime": "regime"})
    trades = pd.merge_asof(
        trades.sort_values("entry_time"),
        regime_df.sort_values("entry_time"),
        on="entry_time",
        direction="backward"
    )

    print("\n" + "="*60)
    print("  REGIMENES DE MERCADO vs PERFORMANCE — US30 518 dias")
    print("="*60)

    # Distribucion de tiempo por regimen
    regime_counts = regimes_df[regimes_df >= 0].value_counts().sort_index()
    total_valid = regime_counts.sum()
    print("\n  Distribucion de tiempo por regimen:")
    for r, cnt in regime_counts.items():
        pct = cnt / total_valid * 100
        print(f"    Regimen {r}: {cnt:5d} velas M5 ({pct:.1f}% del tiempo)")

    # Performance por regimen
    results = []
    regimes = sorted(trades["regime"].dropna().unique())

    print("\n  Performance por regimen:")
    print(f"  {'Reg':>4} {'Trades':>7} {'WR%':>7} {'PF':>6} {'AvgR':>7} {'AvgPnL':>9} {'TotalPnL':>10}")
    print("  " + "-"*56)

    for r in regimes:
        if r == -1:
            continue
        t = trades[trades["regime"] == r]
        n = len(t)
        if n == 0:
            continue

        wins = t[t["pnl_usd"] > 0]
        loss = t[t["pnl_usd"] < 0]
        wr   = len(wins) / n * 100
        pf   = wins["pnl_usd"].sum() / abs(loss["pnl_usd"].sum()) if len(loss) > 0 else 999
        avg_r   = t["pnl_r"].mean() if "pnl_r" in t.columns else 0
        avg_pnl = t["pnl_usd"].mean()
        total   = t["pnl_usd"].sum()

        if n < 20:
            warnings.warn(f"Regimen {r} tiene solo {n} trades — conclusiones poco confiables")

        flag = " << EDGE" if pf > 1.2 and wr > 30 else (" << EVITAR" if pf < 0.9 else "")
        print(f"  {r:>4} {n:>7} {wr:>6.1f}% {pf:>6.2f} {avg_r:>+7.2f}R {avg_pnl:>+9.0f}$ {total:>+10.0f}${flag}")
        results.append({"regime": r, "trades": n, "wr_pct": wr, "pf": pf,
                        "avg_r": avg_r, "avg_pnl": avg_pnl, "total_pnl": total})

    print("="*60)

    # Caracteristicas promedio por regimen
    print("\n  Caracteristicas promedio por regimen (features):")
    feat_means = trades[trades["regime"] >= 0].groupby("regime")[
        [c for c in FEATURE_COLS if c in trades.columns]
    ].mean()
    if not feat_means.empty:
        print(feat_means.round(4).to_string())

    return pd.DataFrame(results)


# --------------------------------------------------------------------------
# 5. Elbow plot — numero optimo de clusters
# --------------------------------------------------------------------------

def find_optimal_clusters(df: pd.DataFrame, scaler, max_k: int = 6):
    """Muestra inertia y silhouette para k=2..max_k."""
    assert SKLEARN_OK
    X = df[FEATURE_COLS].dropna()
    X_scaled = scaler.transform(X)

    inertias, silhouettes = [], []
    ks = range(2, max_k + 1)

    for k in ks:
        km = KMeans(n_clusters=k, random_state=42, n_init=20)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(X_scaled, km.labels_))
        print(f"  k={k}: inertia={km.inertia_:.0f}  silhouette={silhouette_score(X_scaled, km.labels_):.3f}")

    if PLOT_OK:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        ax1.plot(ks, inertias, "bo-")
        ax1.set_title("Elbow Plot — Inertia")
        ax1.set_xlabel("k clusters")
        ax1.set_ylabel("Inertia")

        ax2.plot(ks, silhouettes, "ro-")
        ax2.set_title("Silhouette Score")
        ax2.set_xlabel("k clusters")
        ax2.set_ylabel("Score")

        plt.tight_layout()
        plt.savefig("regime_elbow.png", dpi=120)
        print("  Guardado: regime_elbow.png")
        plt.close()


# --------------------------------------------------------------------------
# 6. Visualizaciones
# --------------------------------------------------------------------------

def plot_regimes(df: pd.DataFrame, trades_df: Optional[pd.DataFrame] = None,
                 n_samples: int = 2000):
    """
    Genera 3 graficos:
      1. Precio con fondo coloreado por regimen
      2. PCA 2D scatter por regimen
      3. Barras de PF y WR por regimen
    """
    if not PLOT_OK:
        print("matplotlib no disponible")
        return

    assert SKLEARN_OK
    colors = ["#2ecc71", "#e74c3c", "#3498db", "#f39c12", "#9b59b6"]
    regime_names = {0: "Reg 0", 1: "Reg 1", 2: "Reg 2", 3: "Reg 3", 4: "Reg 4"}

    df_plot = df[df["regime"] >= 0].copy()
    df_plot["time"] = pd.to_datetime(df_plot["time"])

    fig, axes = plt.subplots(2, 2, figsize=(18, 10))
    fig.suptitle("Market Regime Analysis — US30 M5", fontsize=14, fontweight="bold")

    # --- 1. Precio con fondo por regimen ---
    ax = axes[0, 0]
    sample = df_plot.tail(n_samples)
    ax.plot(sample["time"], sample["close"], color="white", linewidth=0.8, zorder=2)

    regimes = sorted(sample["regime"].unique())
    for r in regimes:
        mask = sample["regime"] == r
        times = sample.loc[mask, "time"]
        if len(times) == 0:
            continue
        for t in times:
            ax.axvspan(t, t + pd.Timedelta(minutes=5),
                      alpha=0.25, color=colors[r % len(colors)], zorder=1)

    patches = [mpatches.Patch(color=colors[r % len(colors)], label=f"Reg {r}", alpha=0.6)
               for r in regimes]
    ax.legend(handles=patches, loc="upper left", fontsize=8)
    ax.set_title(f"Precio + Regimenes (ultimas {n_samples} velas M5)")
    ax.set_facecolor("#1a1a2e")
    ax.tick_params(axis='x', rotation=30, labelsize=7)

    # --- 2. PCA 2D ---
    ax = axes[0, 1]
    valid = df_plot[FEATURE_COLS + ["regime"]].dropna()
    scaler_pca = StandardScaler()
    X_scaled = scaler_pca.fit_transform(valid[FEATURE_COLS])
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    sample_idx = np.random.choice(len(X_pca), min(3000, len(X_pca)), replace=False)
    for r in regimes:
        mask = valid["regime"].values[sample_idx] == r
        ax.scatter(X_pca[sample_idx][mask, 0], X_pca[sample_idx][mask, 1],
                  c=colors[r % len(colors)], alpha=0.4, s=8, label=f"Reg {r}")

    var = pca.explained_variance_ratio_
    ax.set_xlabel(f"PC1 ({var[0]:.1%} varianza)")
    ax.set_ylabel(f"PC2 ({var[1]:.1%} varianza)")
    ax.set_title("PCA 2D — Separacion de regimenes")
    ax.legend(fontsize=8)
    ax.set_facecolor("#1a1a2e")

    # --- 3. PF por regimen (si hay trades) ---
    ax = axes[1, 0]
    if trades_df is not None and "regime" in trades_df.columns:
        pf_data = []
        for r in sorted(trades_df["regime"].dropna().unique()):
            if r == -1: continue
            t = trades_df[trades_df["regime"] == r]
            wins = t[t["pnl_usd"] > 0]["pnl_usd"].sum()
            loss = abs(t[t["pnl_usd"] < 0]["pnl_usd"].sum())
            pf = wins / loss if loss > 0 else 0
            pf_data.append((f"Reg {int(r)}", pf))
        if pf_data:
            labels, vals = zip(*pf_data)
            bar_colors = [colors[int(l.split()[1]) % len(colors)] for l in labels]
            bars = ax.bar(labels, vals, color=bar_colors, alpha=0.8)
            ax.axhline(1.0, color="white", linestyle="--", linewidth=1, alpha=0.5)
            ax.set_title("Profit Factor por Regimen")
            ax.set_ylabel("PF (>1.0 = rentable)")
            ax.set_facecolor("#1a1a2e")
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                       f"{val:.2f}", ha="center", va="bottom", fontsize=9, color="white")

    # --- 4. WR por regimen ---
    ax = axes[1, 1]
    if trades_df is not None and "regime" in trades_df.columns:
        wr_data = []
        for r in sorted(trades_df["regime"].dropna().unique()):
            if r == -1: continue
            t = trades_df[trades_df["regime"] == r]
            wr = len(t[t["pnl_usd"] > 0]) / len(t) * 100 if len(t) > 0 else 0
            wr_data.append((f"Reg {int(r)}", wr))
        if wr_data:
            labels, vals = zip(*wr_data)
            bar_colors = [colors[int(l.split()[1]) % len(colors)] for l in labels]
            bars = ax.bar(labels, vals, color=bar_colors, alpha=0.8)
            ax.axhline(25, color="white", linestyle="--", linewidth=1, alpha=0.5, label="Breakeven ~25%")
            ax.set_title("Win Rate por Regimen")
            ax.set_ylabel("Win Rate %")
            ax.set_facecolor("#1a1a2e")
            ax.legend(fontsize=8)
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       f"{val:.1f}%", ha="center", va="bottom", fontsize=9, color="white")

    plt.tight_layout()
    fig.patch.set_facecolor("#0f0f1a")
    plt.savefig("regime_analysis.png", dpi=130, bbox_inches="tight")
    print("  Guardado: regime_analysis.png")
    plt.close()
