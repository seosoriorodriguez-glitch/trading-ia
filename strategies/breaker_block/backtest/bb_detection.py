# -*- coding: utf-8 -*-
"""
Deteccion de Breaker Blocks — usando la definicion de OB del bot live.

Logica correcta:
  1. Detectar OBs normales (igual que order_block/backtest/ob_detection.py)
     - Bullish OB: vela bajista + N alcistas consecutivas
     - Bearish OB: vela alcista  + N bajistas consecutivas

  2. El OB se marca como DESTROYED cuando:
     - Bullish OB: precio cierra BAJO zone_low  → OB roto hacia abajo
     - Bearish OB: precio cierra SOBRE zone_high → OB roto hacia arriba

  3. Ese OB destruido se convierte en Breaker Block:
     - Bullish OB roto → BB short (ahora es resistencia) → entrada SHORT en pullback
     - Bearish OB roto → BB long  (ahora es soporte)     → entrada LONG  en pullback

  4. Entrada: vela M1 cierra DENTRO del BB → STOP order en borde contrario
     - BB long:  stop BUY  en zone_high (borde superior)
     - BB short: stop SELL en zone_low  (borde inferior)

  Dirección de entrada es CONTRARIA al OB original:
    OB bullish roto → SHORT (bb_type="short")
    OB bearish roto → LONG  (bb_type="long")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from strategies.order_block.backtest.ob_detection import (
    OrderBlock, OBStatus, detect_order_blocks
)


class BBStatus:
    FRESH     = "fresh"      # OB destruido, esperando pullback
    TRIGGERED = "triggered"  # Vela M1 cerro dentro → orden colocada
    EXPIRED   = "expired"    # Demasiadas velas sin pullback
    BROKEN    = "broken"     # BB invalidado (precio cierra al otro lado de zone_low/zone_high)
    MITIGATED = "mitigated"  # Trade abierto, BB consumido


@dataclass
class BreakerBlock:
    """
    Un Breaker Block es un OB que fue destruido y ahora actua al reves.
    bb_type indica la direccion de ENTRADA (contraria al OB original):
      "long"  → OB bearish fue roto hacia arriba → pullback = LONG
      "short" → OB bullish fue roto hacia abajo  → pullback = SHORT
    """
    bb_type:      str      # "long" o "short" (direccion de entrada)
    zone_high:    float    # zona del OB original
    zone_low:     float
    destroyed_at: datetime # cuando el OB fue destruido (= cuando nace el BB)
    ob_type:      str      # "bullish" o "bearish" (tipo del OB original)
    status:       str = field(default=BBStatus.FRESH)


def detect_breaker_blocks(df_m5: pd.DataFrame, params: dict) -> List[BreakerBlock]:
    """
    1. Detecta OBs en M5 usando ob_detection.py
    2. Simula el loop de velas M5 para detectar cuales OBs son destruidos
    3. Retorna lista de BreakerBlocks (OBs destruidos listos para pullback)

    Optimizado: usa puntero ordenado para activar OBs sin iterar toda la lista.
    """
    # Detectar OBs normales
    all_obs = detect_order_blocks(df_m5, params)

    if not all_obs:
        return []

    breakers: List[BreakerBlock] = []
    expiry_c   = params.get("expiry_candles", 100)
    max_active = params.get("max_active_obs", 10)

    rows   = df_m5.to_dict("records")
    n_rows = len(rows)

    # Ordenar OBs por confirmed_at para usar puntero
    sorted_obs = sorted(all_obs, key=lambda o: pd.Timestamp(o.confirmed_at))
    ob_ptr = 0
    n_obs  = len(sorted_obs)

    active_obs = []
    ob_candle_count = {}

    for i, row in enumerate(rows):
        t     = pd.Timestamp(row["time"])
        close = row["close"]

        # Activar OBs cuyo confirmed_at <= tiempo actual (puntero ordenado)
        while ob_ptr < n_obs and pd.Timestamp(sorted_obs[ob_ptr].confirmed_at) <= t:
            ob = sorted_obs[ob_ptr]
            if ob.status == OBStatus.FRESH:
                active_obs.append(ob)
            ob_ptr += 1

        # Limitar max activos (los mas recientes)
        if len(active_obs) > max_active:
            active_obs = sorted(active_obs, key=lambda o: o.confirmed_at, reverse=True)[:max_active]

        # Verificar destruccion y expiry
        still_active = []
        for ob in active_obs:
            if ob.status != OBStatus.FRESH:
                continue

            oid = id(ob)
            ob_candle_count[oid] = ob_candle_count.get(oid, 0) + 1

            # Expiry
            if ob_candle_count[oid] >= expiry_c:
                ob.status = OBStatus.EXPIRED
                continue

            # Destruccion → nace el Breaker Block
            # destroyed_at = open de la SIGUIENTE vela M5 (anti look-ahead)
            # Solo sabemos que el OB fue destruido cuando cierra la vela, no cuando abre
            if i + 1 < n_rows:
                next_t = pd.Timestamp(rows[i + 1]["time"])
            else:
                next_t = t + pd.Timedelta(minutes=5)

            if ob.ob_type == "bullish" and close < ob.zone_low:
                ob.status = OBStatus.DESTROYED
                breakers.append(BreakerBlock(
                    bb_type      = "short",
                    zone_high    = ob.zone_high,
                    zone_low     = ob.zone_low,
                    destroyed_at = next_t,
                    ob_type      = ob.ob_type,
                ))
                continue

            if ob.ob_type == "bearish" and close > ob.zone_high:
                ob.status = OBStatus.DESTROYED
                breakers.append(BreakerBlock(
                    bb_type      = "long",
                    zone_high    = ob.zone_high,
                    zone_low     = ob.zone_low,
                    destroyed_at = next_t,
                    ob_type      = ob.ob_type,
                ))
                continue

            still_active.append(ob)

        active_obs = still_active

    return breakers
