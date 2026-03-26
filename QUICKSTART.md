# 🚀 Guía de Inicio Rápido - Bot de Trading

## ⚡ Setup en 5 Minutos (macOS)

### 1. Instalar Dependencias

```bash
# Ejecutar el script de setup automático
chmod +x setup_mac.sh
./setup_mac.sh
```

Este script instala:
- Docker y Colima (para correr MT5 en Mac)
- Python virtual environment
- Todas las dependencias necesarias

### 2. Configurar Telegram (Opcional pero Recomendado)

```bash
# Copiar el template de variables de entorno
cp .env.example .env

# Editar el archivo .env
nano .env
```

Agregar tus credenciales de Telegram:
```
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

**¿Cómo obtener el token?**
1. Buscar `@BotFather` en Telegram
2. Enviar `/newbot` y seguir instrucciones
3. Copiar el token que te da
4. Enviar un mensaje a tu bot
5. Visitar `https://api.telegram.org/bot<TOKEN>/getUpdates` para obtener tu chat_id

### 3. Conectar MT5

```bash
# El contenedor de MT5 ya está corriendo en el puerto 8001
# Acceder via navegador:
open http://localhost:8001
```

Loguearte con tu cuenta de broker (FTMO, BlackBull, etc.)

### 4. Verificar Símbolos

Abrir MT5 → Vista → Símbolos

Verificar los nombres exactos de los instrumentos (pueden variar por broker):
- US30 → puede ser "US30", "US30.raw", "US30cash", etc.
- NAS100 → puede ser "NAS100", "NAS100.raw", etc.
- SPX500 → puede ser "SPX500", "SPX500.raw", etc.

Actualizar `config/instruments.yaml` con los nombres correctos:

```yaml
instruments:
  US30:
    symbol_mt5: "US30.raw"  # ← Cambiar según tu broker
```

### 5. Ejecutar Backtest

```bash
# Activar el entorno virtual
source venv/bin/activate

# Exportar datos históricos desde MT5
python run_backtest.py --export-mt5 US30 --days 365

# Ejecutar backtest
python run_backtest.py \
  --data-h1 data/US30_raw_H1_365d.csv \
  --data-h4 data/US30_raw_H4_365d.csv \
  --instrument US30 \
  --balance 100000 \
  --output data/backtest_results.csv
```

### 6. Ejecutar Bot en Simulación

```bash
# Modo dry-run (sin ejecutar operaciones reales)
python main.py --log-level INFO
```

El bot mostrará en consola:
- Zonas detectadas
- Señales generadas
- Operaciones simuladas
- Estado de riesgo

---

## 📊 Verificar que Todo Funciona

### Test 1: Conexión a MT5

```bash
python -c "from siliconmetatrader5 import MetaTrader5; mt5=MetaTrader5(host='localhost',port=8001); print('Ping:', mt5.ping())"
```

**Resultado esperado**: `Ping: True`

### Test 2: Cargar Configuración

```bash
python -c "from core.config_loader import get_config; c=get_config(); print('Instrumentos:', list(c.get_enabled_instruments().keys()))"
```

**Resultado esperado**: `Instrumentos: ['US30', 'NAS100', 'SPX500']`

### Test 3: Obtener Velas

```bash
python -c "
from core.market_data import MT5Connection
mt5 = MT5Connection(host='localhost', port=8001)
mt5.connect()
candles = mt5.get_candles('US30.raw', 'H4', 10)
print(f'Velas obtenidas: {len(candles)}')
"
```

**Resultado esperado**: `Velas obtenidas: 10`

---

## 🎯 Próximos Pasos

### Fase 1: Validación (1-2 semanas)
1. ✅ Ejecutar backtest con 2 años de datos
2. ✅ Analizar métricas (Win Rate, Profit Factor, Max DD)
3. ✅ Ajustar parámetros si es necesario
4. ✅ Validar que cumple con reglas FTMO

### Fase 2: Paper Trading (2-4 semanas)
1. Ejecutar bot en cuenta demo FTMO
2. Monitorear operaciones diarias
3. Verificar notificaciones de Telegram
4. Revisar logs y ajustar filtros

### Fase 3: Live Trading (Solo si Fase 1 y 2 son exitosas)
1. FTMO Free Trial (si disponible)
2. FTMO Challenge Phase 1
3. FTMO Challenge Phase 2
4. Cuenta fondeada

---

## 🔧 Comandos Útiles

### Ver Logs en Tiempo Real

```bash
tail -f logs/bot_$(date +%Y%m%d).log
```

### Detener el Bot

```bash
# Presionar Ctrl+C en la terminal donde corre el bot
# O enviar señal SIGTERM:
pkill -f "python main.py"
```

### Reiniciar Contenedor de MT5

```bash
docker restart mt5-trading
```

### Ver Estado del Contenedor

```bash
docker ps | grep mt5-trading
docker logs mt5-trading
```

### Actualizar Dependencias

```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

---

## ❓ Troubleshooting

### Error: "No se pudo conectar a MT5"

**Solución**:
1. Verificar que el contenedor está corriendo: `docker ps`
2. Reiniciar el contenedor: `docker restart mt5-trading`
3. Verificar que MT5 está logueado en el contenedor

### Error: "Symbol not found"

**Solución**:
1. Abrir MT5 → Vista → Símbolos
2. Verificar el nombre exacto del símbolo
3. Actualizar `config/instruments.yaml` con el nombre correcto

### Error: "Telegram bot not responding"

**Solución**:
1. Verificar que el token es correcto en `.env`
2. Verificar que el bot está activo en Telegram
3. Enviar un mensaje al bot para activarlo
4. Verificar el chat_id visitando la URL de getUpdates

### El bot no genera señales

**Posibles causas**:
1. No hay zonas válidas detectadas (revisar logs)
2. El precio no está cerca de ninguna zona
3. Los filtros de spread o volatilidad están bloqueando
4. El mercado está cerrado (fin de semana)

**Solución**: Revisar logs con `--log-level DEBUG`

---

## 📚 Más Información

- **Documentación completa**: [PROYECTO_OVERVIEW.md](PROYECTO_OVERVIEW.md)
- **Estrategia detallada**: [docs/estrategia_sr_indices.md](docs/estrategia_sr_indices.md)
- **Configuración**: Ver archivos en `config/`

---

**¡Listo! Tu bot está configurado y listo para operar. 🚀**

Recuerda: **SIEMPRE** hacer backtest y paper trading antes de usar dinero real.
