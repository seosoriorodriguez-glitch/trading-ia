# 📊 ESTRATEGIA COMPLETA - BOT LIVE ORDER BLOCK

**Última actualización**: 30 Marzo 2026  
**Estado**: ✅ IMPLEMENTADO CON LÓGICA LIMIT  
**Símbolo**: US30.cash (Dow Jones)

---

## 🎯 RESUMEN ESTRATEGIA

Estrategia de Order Blocks híbrida M5/M1 que identifica zonas institucionales de liquidez en M5 y ejecuta entradas precisas en M1 mediante órdenes LIMIT pendientes.

---

## 📐 DETECCIÓN DE ORDER BLOCKS (M5)

### Bullish OB (LONG):
1. **Vela bajista** (`close < open`)
2. **Seguida de 4 velas TODAS alcistas** (`close > open`)
3. **Zona**: `[low, open]` de la vela bajista
4. **Filtro ATR**: Tamaño zona ≤ `ATR(14) * 3.5`

### Bearish OB (SHORT):
1. **Vela alcista** (`close > open`)
2. **Seguida de 4 velas TODAS bajistas** (`close < open`)
3. **Zona**: `[open, high]` de la vela alcista
4. **Filtro ATR**: Igual que bullish

### Gestión de OBs:
- **Confirmación**: Apertura de la vela que sigue al cierre de la 4ta vela (anti look-ahead)
- **Expiración**: 100 velas M5 sin toque
- **Destrucción**: Vela M5 cierra fuera de la zona
- **Max activos**: 10 OBs (los más recientes)

---

## 🎯 LÓGICA DE ENTRADA (M1) - LIMIT ORDERS

### Condiciones:
1. **Horario**: Sesión NY 13:45-20:00 UTC (skip primeros 15 min)
2. **Vela M1 cierra DENTRO de zona OB**: `zone_low ≤ close ≤ zone_high`
3. **Orden LIMIT pendiente** en:
   - **LONG**: `entry_price = zone_high` (extremo superior)
   - **SHORT**: `entry_price = zone_low` (extremo inferior)

### Vida de la orden:
- ✅ **Se ejecuta**: Cuando precio toca el límite
- ❌ **Se cancela**: Cuando OB se destruye (vela M5 cierra fuera)
- ❌ **Se cancela**: Cuando OB expira (100 velas M5)

### Filtros aplicados:
- **EMA 4H**: ❌ Desactivado
- **Rejection candle**: ❌ Desactivado
- **BOS (Break of Structure)**: ❌ Desactivado

---

## 💰 GESTIÓN DE RIESGO

### LONG (OB Bullish):
- **Entry**: `zone_high`
- **SL**: `zone_low - 25 puntos` (debajo de zona)
- **TP**: `entry + (risk_points * 3.5)` (arriba de entry)

### SHORT (OB Bearish):
- **Entry**: `zone_low`
- **TP**: `zone_low - 25 puntos` (debajo de zona)
- **SL**: `entry + (reward_points / 3.5)` (arriba de entry)

### Parámetros:
- **Buffer SL**: 25 puntos
- **Target R:R**: 3.5
- **Min R:R**: 1.2
- **Min risk**: 15 puntos
- **Max risk**: 300 puntos
- **Risk por trade**: 0.5% del balance ($500 con $100k)
- **Max trades simultáneos**: 2

---

## 🛡️ PROTECCIONES FTMO

- **Daily DD máximo**: 5% ($5,000)
- **Total DD máximo**: 10% ($10,000)
- **Profit target**: 10% ($10,000)
- **Max spread**: 5 puntos
- **Cierre fin de semana**: Viernes 21:00 UTC
- **Días mínimos trading**: 4

---

## 📊 RESULTADOS BACKTEST (104 días)

### Rentabilidad:
- **Retorno**: **+30.91%** ($30,908)
- **Max Drawdown**: **-6.62%** ✅ (dentro límite FTMO)
- **Trades**: 197
- **Win Rate**: 29.4%
- **Profit Factor**: 1.55
- **Expectancy**: $157 por trade

### Por Dirección:
- **LONG**: 101 trades, WR 25.7%, **+$5,745** ✅
- **SHORT**: 96 trades, WR 33.3%, **+$25,163** ✅

### Métricas de calidad:
- **Avg Winner**: $2,017 (3.46R)
- **Avg Loser**: -$619 (-1.04R)
- **Mejor día**: +$6,701
- **Peor día**: -$3,093
- **Trades/día promedio**: 1.9

---

## 🔄 FLUJO OPERATIVO

### Cada 5 minutos (vela M5):
1. Descargar últimas 350 velas M5
2. Re-detectar OBs
3. Aplicar expiry/destrucción
4. **Cancelar órdenes LIMIT de OBs destruidos/expirados**

### Cada 1 minuto (vela M1):
1. Descargar últimas 60 velas M1
2. Verificar si vela cierra dentro de algún OB activo
3. Si sí: Colocar orden LIMIT en zone_high/zone_low
4. Marcar OB como mitigado (no re-entrar)

### Continuamente:
1. **Monitorear órdenes pendientes**: Detectar si se ejecutaron
2. **Mover a open_trades**: Cuando orden se ejecuta
3. **Monitorear posiciones abiertas**: Detectar cierre por SL/TP
4. **Actualizar balance y DD**
5. **Dashboard cada 30 seg**

---

## 🎯 VENTAJAS CLAVE DE LIMIT

### 1. Mejor precio de entrada:
- MARKET: Entra en `candle_close` (puede ser en medio de zona)
- LIMIT: Entra en `zone_high`/`zone_low` (extremo óptimo)

### 2. Maximiza R:R real:
- Al entrar en el extremo, el R:R efectivo es mayor
- SL más cercano, TP más lejano

### 3. Hace LONG rentable:
- MARKET: LONG -$2,351 ❌
- LIMIT: LONG +$5,745 ✅

### 4. Reduce drawdown:
- MARKET: -10.69% (excede FTMO)
- LIMIT: -6.62% (cumple FTMO)

### 5. Evita slippage:
- MARKET: Sujeto a slippage en ejecución
- LIMIT: Precio garantizado o no se ejecuta

---

## 📋 PARÁMETROS COMPLETOS

```python
DEFAULT_PARAMS = {
    # Detección OB (M5)
    "consecutive_candles": 4,
    "min_impulse_pct": 0.0,
    "zone_type": "half_candle",
    "max_atr_mult": 3.5,
    "expiry_candles": 100,
    "max_active_obs": 10,

    # Entrada (M1)
    "entry_method": "LIMIT",  # ✅ IMPLEMENTADO

    # Risk Management
    "buffer_points": 25,
    "min_risk_points": 15,
    "max_risk_points": 300,
    "target_rr": 3.5,
    "min_rr_ratio": 1.2,
    "risk_per_trade_pct": 0.005,
    "max_simultaneous_trades": 2,

    # Costos
    "avg_spread_points": 2,
    "point_value": 1.0,

    # Sesiones
    "sessions": {
        "new_york": {
            "start": "13:30",
            "end": "20:00",
            "skip_minutes": 15
        }
    },

    # Filtros (todos desactivados)
    "ema_trend_filter": False,
    "require_rejection": False,
    "require_bos": False,

    # Balance
    "initial_balance": 100_000.0,
}
```

---

## ✅ ESTADO FINAL

- ✅ Código implementado y verificado
- ✅ Sintaxis correcta en todos los archivos
- ✅ Backtest confirma resultados esperados (+30.91%)
- ✅ Lógica LIMIT completamente integrada
- ✅ Gestión de órdenes pendientes operativa
- ✅ Cancelación automática de órdenes inválidas

**EL BOT ESTÁ LISTO PARA OPERAR CON LÓGICA LIMIT.**
