@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================================
echo 🤖 INICIANDO BOT FTMO - PIVOT SCALPING
echo ============================================================
echo.
echo Activando entorno virtual...
call venv\Scripts\activate.bat
echo.
echo Ejecutando bot en modo LIVE...
echo Presiona Ctrl+C para detener
echo.
python run_live_bot.py
echo.
echo Bot detenido.
pause
