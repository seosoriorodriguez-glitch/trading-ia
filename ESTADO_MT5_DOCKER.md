# 🐳 Estado de MT5 en Docker - Problema y Soluciones

**Fecha**: 26 de Marzo, 2026  
**Problema**: Las imágenes Docker de MT5 especificadas no están disponibles

---

## ❌ Imágenes Probadas (No Disponibles)

### 1. `bahadirumutiscimen/pysiliconwine:latest`
```
Error: docker.io/bahadirumutiscimen/pysiliconwine:latest: not found
```

### 2. `alfiej04/metatrader5:latest`
```
Error: docker.io/alfiej04/metatrader5:latest: not found
```

---

## 🔍 Opciones de Solución

### Opción A: Buscar Imagen MT5 Alternativa

**Imágenes potenciales para probar**:
1. `scottyhardy/docker-wine` + instalación manual de MT5
2. `linuxserver/rdesktop` + Wine + MT5
3. Crear imagen custom basada en Ubuntu + Wine + MT5

**Problema**: Requiere tiempo de investigación y configuración.

### Opción B: MT5 Nativo en macOS (Recomendado para desarrollo)

**Pasos**:
1. Descargar MT5 para macOS desde https://www.metatrader5.com/en/download
2. Instalar y configurar cuenta demo/real
3. Usar `MetaTrader5` Python package (no `siliconmetatrader5`)
4. Conectar directamente sin Docker

**Ventajas**:
- Más rápido de configurar
- Mejor rendimiento
- Acceso directo a MT5
- No depende de emulación

**Desventajas**:
- Solo funciona en la máquina local
- No es portable

### Opción C: Plan B Temporal - Datos de Fuentes Alternativas ✅ IMPLEMENTANDO

**Fuentes de datos M5 gratuitas**:

1. **Dukascopy** (Recomendado)
   - URL: https://www.dukascopy.com/swiss/english/marketwatch/historical/
   - Datos: Tick, M1, M5, M15, H1, H4, D1
   - Formato: CSV descargable
   - Calidad: Excelente (broker suizo regulado)
   - Instrumentos: Forex, índices, commodities

2. **FirstRate Data**
   - URL: https://firstratedata.com
   - Datos: M1, M5, M15, H1, H4, D1
   - Formato: CSV
   - Calidad: Buena
   - Instrumentos: Forex principalmente

3. **Histdata.com**
   - URL: http://www.histdata.com
   - Datos: Tick, M1
   - Formato: CSV
   - Calidad: Buena
   - Limitación: Solo M1 (necesitamos resamplear a M5)

4. **Yahoo Finance** (Ya implementado)
   - Datos: M15, H1, H4, D1
   - Limitación: **NO tiene M5**
   - Período: M15 solo 60 días

---

## ✅ Decisión: Plan B Temporal + Búsqueda de Solución Permanente

### Acción Inmediata

1. **Implementar descarga de Dukascopy** para obtener datos M5 reales
2. **Continuar con el backtest** usando estos datos
3. **Documentar claramente** que los resultados son con datos de Dukascopy

### Acción Paralela

1. **Investigar imagen Docker funcional** para MT5 en Apple Silicon
2. **Considerar MT5 nativo** en macOS como alternativa
3. **Documentar solución** una vez encontrada

---

## 📝 Nota Importante

**Los datos de Dukascopy son de calidad institucional** y son ampliamente usados por traders profesionales para backtesting. Los resultados serán válidos y confiables.

**Sin embargo**, para trading en vivo (demo o real), **SÍ necesitamos MT5 conectado**. Esto es prioritario antes de pasar a FTMO.

---

## 🎯 Próximos Pasos

1. ✅ Crear `download_dukascopy_data.py` para obtener M5 y M15
2. ✅ Descargar datos de US30 (60 días)
3. ✅ Continuar con implementación de estrategia de scalping
4. ⏳ Investigar solución MT5 en paralelo
5. ⏳ Validar en demo una vez MT5 esté disponible

---

## 🔧 Comandos para Cuando MT5 Esté Disponible

```bash
# Verificar conexión
python3 verify_connection.py

# Descargar datos
python3 download_mt5_data.py --symbol US30 --timeframes M5 M15 --days 60

# Ejecutar backtest
python3 run_scalping_backtest.py \
  --data-m5 data/US30_M5_60d.csv \
  --data-m15 data/US30_M15_60d.csv \
  --instrument US30
```

---

**Estado**: 🟡 Bloqueado en Docker, procediendo con Plan B (Dukascopy)
