# 🪟 Setup en Windows (Lenovo) - Guía Completa

**Repositorio**: https://github.com/seosoriorodriguez-glitch/trading-ia  
**Plataforma**: Windows  
**Fecha**: 26 de Marzo, 2026

---

## 🚀 Instalación Rápida

### Paso 1: Instalar Requisitos Previos

#### 1.1 Python 3.10+
```bash
# Descargar desde: https://www.python.org/downloads/
# Durante instalación: ✅ Add Python to PATH
```

Verificar:
```bash
python --version
# Debe mostrar: Python 3.10.x o superior
```

#### 1.2 Git
```bash
# Descargar desde: https://git-scm.com/download/win
```

Verificar:
```bash
git --version
```

#### 1.3 MetaTrader 5
```bash
# Descargar desde: https://www.metatrader5.com/en/download
# Instalar y abrir
```

### Paso 2: Clonar Repositorio

```bash
# Abrir PowerShell o CMD
cd C:\Users\TU_USUARIO\Documents
git clone https://github.com/seosoriorodriguez-glitch/trading-ia.git
cd trading-ia
```

### Paso 3: Crear Entorno Virtual

```bash
python -m venv venv
venv\Scripts\activate
```

**Verificar que el entorno esté activo**:
```bash
# El prompt debe mostrar: (venv) C:\...\trading-ia>
```

### Paso 4: Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Verificar instalación**:
```bash
pip list | findstr MetaTrader5
# Debe mostrar: MetaTrader5  5.0.x
```

### Paso 5: Configurar MetaTrader 5

#### 5.1 Abrir Cuenta Demo (si no tienes)

1. Abrir MT5
2. File → Open an Account
3. Seleccionar broker:
   - **FTMO** (recomendado para práctica)
   - O tu broker preferido
4. Completar formulario
5. Loguear con credenciales

#### 5.2 Habilitar Algo Trading

1. Tools → Options
2. Tab "Expert Advisors"
3. ✅ Allow automated trading
4. ✅ Allow DLL imports (opcional)
5. Click OK

#### 5.3 Verificar Símbolos

1. View → Market Watch (Ctrl+M)
2. Buscar símbolos:
   - US30 (o variantes: US30.cash, US30.raw)
   - NAS100
   - SPX500
3. Click derecho → Show (para hacerlos visibles)

### Paso 6: Verificar Conexión

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
Balance:       $100,000.00
...

================================================================================
  BÚSQUEDA DE SÍMBOLOS
================================================================================

🔍 Buscando US30...
   ✅ Encontrado: US30.cash
      Descripción:    Dow Jones Industrial Average
      Spread:         2 puntos
      ...
```

**Si falla**:
- ❌ Verificar que MT5 esté ejecutándose
- ❌ Verificar que estés logueado
- ❌ Verificar que Algo Trading esté habilitado

### Paso 7: Descargar Datos

```bash
# Usar el nombre de símbolo correcto del Paso 6
python tools/download_mt5_data.py \
  --symbol US30.cash \
  --timeframes M5 M15 \
  --days 60
```

**Output esperado**:
```
================================================================================
  DESCARGA DE DATOS MT5
================================================================================

✅ Conectado — Cuenta: 12345678, Broker: FTMO Demo

📥 Descargando M5...
✅ 17280 velas descargadas
💾 data/US30_cash_M5_60d.csv

📥 Descargando M15...
✅ 5760 velas descargadas
💾 data/US30_cash_M15_60d.csv
```

**Verificar archivos**:
```bash
dir data\*.csv
# Debe mostrar: US30_cash_M5_60d.csv, US30_cash_M15_60d.csv
```

---

## 🎯 Próximos Pasos

### 1. Actualizar Configuración

Editar `strategies/pivot_scalping/config/instruments.yaml`:

```yaml
instruments:
  US30:
    symbol_mt5: "US30.cash"  # ← Usar nombre real del Paso 6
```

### 2. Continuar Implementación

La estrategia de scalping está ~30% completada:

- ✅ Configuración (`scalping_params.yaml`)
- ✅ Detección de pivots (`pivot_detection.py`)
- ⏳ Generación de señales (pendiente)
- ⏳ Backtester (pendiente)

### 3. Ejecutar Backtest

Una vez completada la implementación:

```bash
cd strategies/pivot_scalping
python run_scalping_backtest.py \
  --data-m5 ../../data/US30_cash_M5_60d.csv \
  --data-m15 ../../data/US30_cash_M15_60d.csv \
  --instrument US30 \
  --output data/backtest_US30_scalping_v1.csv
```

---

## 🔧 Comandos Útiles

### Actualizar Repositorio

```bash
# Obtener últimos cambios
git pull origin main

# Ver estado
git status

# Ver commits recientes
git log --oneline -10
```

### Activar Entorno Virtual

```bash
# Cada vez que abras una nueva terminal
cd C:\Users\TU_USUARIO\Documents\trading-ia
venv\Scripts\activate
```

### Ejecutar Herramientas

```bash
# Verificar conexión MT5
python tools/verify_connection.py

# Descargar datos
python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 M15 --days 60

# Comparar estrategias
python tools/compare_strategies.py strategies/sr_swing/data/*.csv

# Crear nueva estrategia
python tools/create_strategy.py mi_estrategia
```

---

## ⚠️ Troubleshooting

### Error: "MT5 initialize() falló"

**Soluciones**:
1. Verificar que MT5 esté ejecutándose
2. Verificar que estés logueado en una cuenta
3. Reiniciar MT5
4. Verificar que Algo Trading esté habilitado

### Error: "Símbolo no encontrado"

**Soluciones**:
1. Ejecutar `python tools/verify_connection.py` para ver símbolos disponibles
2. Verificar que el símbolo esté visible en Market Watch
3. Probar variantes: `US30`, `US30.cash`, `US30.raw`

### Error: "No se pudieron obtener velas"

**Soluciones**:
1. Verificar que el símbolo tenga datos históricos
2. Reducir el número de días solicitados
3. Verificar conexión a internet (MT5 descarga datos del servidor)

### Error: "ModuleNotFoundError: No module named 'MetaTrader5'"

**Solución**:
```bash
# Activar entorno virtual
venv\Scripts\activate

# Reinstalar
pip install MetaTrader5
```

---

## 📊 Verificación de Setup Exitoso

**Checklist**:
- [ ] Python 3.10+ instalado
- [ ] Git instalado
- [ ] Repositorio clonado
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas (`pip list | findstr MetaTrader5`)
- [ ] MT5 instalado y ejecutándose
- [ ] Cuenta demo/real logueada en MT5
- [ ] Algo Trading habilitado
- [ ] `verify_connection.py` ejecutado exitosamente
- [ ] Datos M5/M15 descargados

**Si todos los checks están ✅, estás listo para continuar con el desarrollo!**

---

## 🎉 ¡Listo!

Tu entorno de desarrollo está configurado. Ahora puedes:

1. **Continuar implementación** de estrategia de scalping
2. **Ejecutar backtests** con datos reales de MT5
3. **Validar en demo** antes de FTMO
4. **Iterar y crear** nuevas estrategias

---

## 💡 Tips

### Mantener Sincronizado

```bash
# Antes de empezar a trabajar
git pull origin main

# Después de hacer cambios
git add .
git commit -m "Descripción de cambios"
git push origin main
```

### Backup de Datos

Los archivos CSV en `data/` **NO se suben a GitHub** (están en `.gitignore`).

**Recomendación**: Hacer backup manual de:
- `data/*.csv` - Datos históricos
- `strategies/*/data/*.csv` - Resultados de backtests

### Organización

- Una estrategia = una carpeta en `strategies/`
- Cada estrategia tiene su propio README
- Usar `tools/create_strategy.py` para nuevas estrategias

---

**¿Preguntas?** Revisa la documentación o abre un issue en GitHub.

**¡Buena suerte con el setup!** 🚀
