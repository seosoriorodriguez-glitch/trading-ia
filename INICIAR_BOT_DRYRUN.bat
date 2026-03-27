@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================================
echo 🧪 INICIANDO BOT EN MODO DRY-RUN (PRUEBA)
echo ============================================================
echo.
echo Activando entorno virtual...
call venv\Scripts\activate.bat
echo.
echo Ejecutando bot en modo DRY-RUN...
echo Presiona Ctrl+C para detener
echo.
python run_live_bot.py --dry-run
echo.
echo Bot detenido.
pause
