#!/usr/bin/env python3
"""
Script temporal para forzar recarga de módulos y ejecutar backtest V4.
"""
import sys
import os

# Limpiar cache de módulos
for module_name in list(sys.modules.keys()):
    if module_name.startswith('core.') or module_name.startswith('backtest.'):
        del sys.modules[module_name]

# Ejecutar backtest
from run_backtest import main

sys.argv = [
    'run_backtest.py',
    '--data-h1', 'data/US30_H1_730d.csv',
    '--data-h4', 'data/US30_H4_730d.csv',
    '--instrument', 'US30',
    '--balance', '100000',
    '--output', 'data/backtest_US30_v4_longs_only.csv'
]

if __name__ == '__main__':
    main()
