# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

print("Descargando M1 con límite conservador...")

if not mt5.initialize():
    print(f"Error inicializando MT5: {mt5.last_error()}")
    sys.exit(1)

symbol = "US30.cash"

# Intentar con 30,000 velas (aproximadamente 20 días de trading)
print(f"Intentando descargar 30,000 velas M1...")
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 30000)

if rates is None or len(rates) == 0:
    print(f"Error: {mt5.last_error()}")
    mt5.shutdown()
    sys.exit(1)

print(f"✅ Descargadas {len(rates)} velas M1")

# Convertir a DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

print(f"Rango: {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
print(f"Días: {(df['time'].iloc[-1] - df['time'].iloc[0]).days}")

# Guardar
output_file = 'data/US30_cash_M1_30k.csv'
df.to_csv(output_file, index=False)
print(f"💾 Guardado en {output_file}")

mt5.shutdown()
