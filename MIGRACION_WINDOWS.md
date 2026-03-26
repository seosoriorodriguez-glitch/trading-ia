# 🪟 Migración a Windows - MT5 Nativo

**Fecha**: 26 de Marzo, 2026  
**Plataforma**: Windows (Lenovo)  
**Librería**: MetaTrader5 (oficial de MetaQuotes)

---

## ✅ CAMBIOS COMPLETADOS

### 1. Limpieza de Código macOS/Docker

**Eliminados**:
- ❌ `docker-compose.yml` - Ya no necesario
- ❌ `setup_mac.sh` - Script específico de macOS
- ❌ Referencias a `siliconmetatrader5` en código

### 2. Actualización de Dependencias

**`requirements.txt`** actualizado:
```txt
# MetaTrader 5 (Windows - Librería Oficial)
MetaTrader5>=5.0.45

# Dependencias Core
pandas>=2.0
numpy>=1.24
PyYAML>=6.0
requests>=2.31
matplotlib>=3.7
yfinance>=0.2.28
```

### 3. Actualización de `core/market_data.py`

**Cambios**:
- ✅ Eliminado fallback a `siliconmetatrader5`
- ✅ Usa solo `import MetaTrader5 as mt5`
- ✅ Conexión directa sin Docker
- ✅ Simplificado `MT5Connection.__init__()` (sin host/port)
- ✅ Todas las llamadas usan `mt5.` directamente

**Antes**:
```python
def __init__(self, host: str = "localhost", port: int = 8001):
    # Intentar Windows, luego macOS/Docker...
```

**Ahora**:
```python
def __init__(self):
    # Solo Windows, conexión directa
    if not mt5.initialize():
        # Error handling
```

### 4. Nuevos Scripts para Windows

#### `tools/verify_connection.py`

**Propósito**: Verificar conexión a MT5 y descubrir nombres de símbolos

**Características**:
- Conecta a MT5 local
- Muestra info de cuenta (login, broker, balance)
- Busca variantes de símbolos:
  - US30: `US30`, `US30.cash`, `US30.raw`, `US30Cash`, etc.
  - NAS100, SPX500, EURUSD, GBPUSD, GBPJPY
- Muestra características de cada símbolo (point, spread, contract size)
- Prueba descarga de velas (M5, M15, H1, H4)
- Genera resumen para copiar a configuración

**Uso**:
```bash
python tools/verify_connection.py
```

**Output esperado**:
```
================================================================================
  VERIFICACIÓN DE CONEXIÓN MT5
================================================================================

📡 Intentando conectar a MetaTrader 5...
✅ Conectado a MetaTrader 5

================================================================================
  INFORMACIÓN DE CUENTA
================================================================================
Cuenta:        12345678
Broker:        FTMO Demo
Servidor:      FTMO-Demo
Balance:       $100,000.00
...

================================================================================
  BÚSQUEDA DE SÍMBOLOS
================================================================================

🔍 Buscando US30...
   ✅ Encontrado: US30.cash
      Descripción:    Dow Jones Industrial Average
      Point:          0.01
      Digits:         2
      Spread:         2 puntos
      ...
```

#### `tools/download_mt5_data.py`

**Propósito**: Descargar datos históricos directamente de MT5

**Características**:
- Conexión directa a MT5 (sin Docker, sin HTTP)
- Descarga múltiples timeframes en una ejecución
- Calcula automáticamente número de velas necesarias
- Verifica calidad de datos (gaps, NaNs)
- Guarda en formato CSV estándar
- Muestra progreso y resumen

**Uso**:
```bash
# Descargar M5 y M15 de US30 (60 días)
python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 M15 --days 60

# Descargar todos los timeframes (2 años)
python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 M15 H1 H4 --days 730

# Output personalizado
python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 --days 60 --output custom_data
```

**Output esperado**:
```
================================================================================
  DESCARGA DE DATOS MT5
================================================================================

📡 Conectando a MetaTrader 5...
✅ Conectado — Cuenta: 12345678, Broker: FTMO Demo

✅ Símbolo verificado: US30.cash
   Descripción: Dow Jones Industrial Average

📥 Descargando M5...
   Símbolo:  US30.cash
   Días:     60
   Velas:    ~20736
✅ 17280 velas descargadas
   Rango: 2026-01-26 14:30:00 → 2026-03-26 19:55:00
   Último precio: 45955.00
💾 data/US30_cash_M5_60d.csv

📥 Descargando M15...
...
```

---

## 🚀 PRÓXIMOS PASOS (En Windows)

### Paso 1: Configuración Inicial

```bash
# 1. Clonar/copiar proyecto en Windows
# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Paso 2: Configurar MT5

1. **Instalar MetaTrader 5**:
   - Descargar desde: https://www.metatrader5.com/en/download
   - Instalar en Windows

2. **Abrir cuenta demo/real**:
   - Abrir MT5
   - File → Open an Account
   - Seleccionar broker (ej: FTMO)
   - Loguear con credenciales

3. **Habilitar Algo Trading**:
   - Tools → Options
   - Expert Advisors tab
   - ✅ Allow automated trading
   - ✅ Allow DLL imports (si es necesario)

### Paso 3: Verificar Conexión

```bash
python tools/verify_connection.py
```

**Verificar**:
- ✅ Conexión exitosa
- ✅ Info de cuenta mostrada
- ✅ Símbolos encontrados (US30, NAS100, etc.)
- ✅ Velas descargadas correctamente

**Si falla**:
- Verificar que MT5 esté ejecutándose
- Verificar que estés logueado
- Verificar que Algo Trading esté habilitado

### Paso 4: Descargar Datos

```bash
# Usar el nombre de símbolo correcto encontrado en Paso 3
python tools/download_mt5_data.py \
  --symbol US30.cash \
  --timeframes M5 M15 \
  --days 60
```

**Verificar**:
- ✅ Archivos CSV creados en `data/`
- ✅ Número de velas correcto
- ✅ Rango de fechas correcto

### Paso 5: Continuar con Estrategia

Una vez que tengas los datos:

1. **Actualizar configuración** con nombres de símbolos reales
2. **Continuar implementación** de estrategia de scalping
3. **Ejecutar backtest** con datos reales de MT5

---

## 📊 Comparación: Antes vs Ahora

### Antes (macOS + Docker)

```
┌─────────────┐
│   macOS     │
│             │
│  ┌────────┐ │      HTTP:8001      ┌──────────┐
│  │ Python │ │ ──────────────────> │  Docker  │
│  │ Script │ │                     │          │
│  └────────┘ │                     │  ┌────┐  │
│             │                     │  │MT5 │  │
│             │                     │  └────┘  │
└─────────────┘                     └──────────┘
                                    (QEMU x86)
```

**Problemas**:
- ❌ Imágenes Docker no disponibles
- ❌ Emulación lenta (QEMU)
- ❌ Configuración compleja
- ❌ Dependencia de Docker

### Ahora (Windows Nativo)

```
┌─────────────┐
│  Windows    │
│             │
│  ┌────────┐ │   Direct API   ┌────┐
│  │ Python │ │ ─────────────> │MT5 │
│  │ Script │ │                └────┘
│  └────────┘ │                (Nativo)
│             │
└─────────────┘
```

**Ventajas**:
- ✅ Conexión directa (sin Docker)
- ✅ Rendimiento nativo
- ✅ Configuración simple
- ✅ Librería oficial de MetaQuotes
- ✅ Sin dependencias externas

---

## 🔧 Archivos Modificados

### Eliminados (2)
- `docker-compose.yml`
- `setup_mac.sh`

### Modificados (2)
- `requirements.txt` - Actualizado para Windows
- `core/market_data.py` - Reescrito para MT5 nativo

### Creados (2)
- `tools/verify_connection.py` - Verificación de conexión
- `tools/download_mt5_data.py` - Descarga de datos

---

## 📝 Notas Importantes

### Compatibilidad

**Este proyecto ahora está optimizado para Windows**. Si necesitas ejecutarlo en macOS/Linux:
1. Reinstalar Docker y configurar MT5 en contenedor
2. Revertir cambios en `core/market_data.py`
3. Usar `siliconmetatrader5` en lugar de `MetaTrader5`

### Nombres de Símbolos

Los nombres de símbolos **varían por broker**:
- FTMO: `US30.cash`, `NAS100.cash`, `SPX500.cash`
- Otros: `US30`, `US30.raw`, `USA30`, etc.

**Siempre ejecutar `verify_connection.py` primero** para descubrir los nombres correctos.

### Datos Históricos

MT5 tiene límites en la cantidad de datos históricos:
- **M1/M5**: ~2-3 meses típicamente
- **M15/H1**: ~1-2 años
- **H4/D1**: Varios años

Para backtesting extenso, considerar:
1. Descargar y guardar datos periódicamente
2. Usar fuentes alternativas (Dukascopy, FirstRate Data)
3. Combinar múltiples descargas

---

## ✅ Estado Actual

**Migración**: ✅ COMPLETADA  
**Plataforma**: Windows  
**MT5**: Listo para conectar  
**Scripts**: Creados y documentados  
**Siguiente**: Probar en Windows y descargar datos

---

**¿Listo para probar en Windows?**

1. Abre el proyecto en tu Lenovo (Windows)
2. Ejecuta `python tools/verify_connection.py`
3. Descarga datos con `download_mt5_data.py`
4. Continúa con la implementación de la estrategia de scalping
