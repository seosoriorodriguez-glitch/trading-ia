# ⚡ Comandos Rápidos - Bot FTMO

## 🚀 Iniciar Bot

### Modo Live (FTMO Trial)
```powershell
cd C:\Users\sosor\OneDrive\Escritorio\dev\trading\trading-ia
.\venv\Scripts\activate.ps1
python run_live_bot.py
```

### Modo Dry-Run (Testing)
```powershell
cd C:\Users\sosor\OneDrive\Escritorio\dev\trading\trading-ia
.\venv\Scripts\activate.ps1
python run_live_bot.py --dry-run
```

### Sin Telegram
```powershell
python run_live_bot.py --no-telegram
```

---

## 🛑 Detener Bot

### Opción 1: Ctrl+C
Presionar `Ctrl+C` en la consola

### Opción 2: Archivo STOP.txt
```powershell
echo "" > STOP.txt
```

---

## 📊 Ver Logs

### Trades de Hoy
```powershell
type logs\trades_*.csv | more
```

### Últimos Eventos
```powershell
type logs\bot_*.log | more
```

### Errores
```powershell
type logs\errors_*.log | more
```

---

## 🔍 Verificar Estado

### Ver Procesos Python
```powershell
tasklist | findstr python
```

### Matar Proceso (si se colgó)
```powershell
taskkill /F /IM python.exe
```

---

## 📱 Test Telegram

```powershell
python -c "import asyncio; from telegram import Bot; asyncio.run(Bot('8577007615:AAHy31IegzvbezCpyNfIlaZh_IsKuV-4M9A').send_message('6265548967', 'Test OK'))"
```

---

## 🔧 Reinstalar Dependencias

```powershell
.\venv\Scripts\activate.ps1
pip install --upgrade MetaTrader5 pandas numpy pyyaml python-telegram-bot
```

---

## 📈 Backtest Rápido (Validación)

```powershell
python strategies/pivot_scalping/run_backtest_m5m1.py --data-m1 data/US30_cash_M1_29d.csv --data-m5 data/US30_cash_M5_29d.csv --instrument US30 --config strategies/pivot_scalping/config/scalping_params_M5M1_aggressive.yaml --output test_backtest.csv
```

---

## 🧹 Limpiar Logs Antiguos

```powershell
del logs\*.csv
del logs\*.log
```

---

## ✅ Checklist Rápido

Antes de iniciar en FTMO:

```powershell
# 1. Verificar MT5 conectado
# 2. Activar venv
.\venv\Scripts\activate.ps1

# 3. Test rápido (30s)
python run_live_bot.py --dry-run

# 4. Si todo OK, iniciar en live
python run_live_bot.py
```

---

## 🆘 Troubleshooting Rápido

### Error: "Cannot connect to MT5"
```powershell
# Verificar que MT5 está abierto y conectado
# Reiniciar MT5 si es necesario
```

### Error: "Symbol not found"
```powershell
# En MT5: Market Watch → Click derecho → Mostrar todo
# Buscar US30.cash y agregar
```

### Bot no responde
```powershell
# Crear archivo STOP.txt
echo "" > STOP.txt

# Si no funciona, matar proceso
taskkill /F /IM python.exe
```

---

## 📞 Contacto Rápido

**Telegram Bot:** `@your_bot_name`  
**Chat ID:** `6265548967`

---

**¡Listo para operar! 🚀**
