@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================================
echo 🧪 TEST DE TRADE MANUAL - COMPRA Y VENTA RAPIDA
echo ============================================================
echo.
echo IMPORTANTE: Este script ejecutara un trade REAL de prueba
echo - Volumen minimo: 0.01 lotes
echo - Tipo: COMPRA (LONG)
echo - SL: -50 puntos
echo - TP: +30 puntos
echo.
echo El trade se cerrara manualmente despues de 3 segundos.
echo.
pause
echo.
echo Activando entorno virtual...
call venv\Scripts\activate.bat
echo.
python test_trade_manual.py
echo.
pause
