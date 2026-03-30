# -*- coding: utf-8 -*-
"""
Script de verificación rápida del estado del bot Order Block.
Verifica configuración, horarios, y estado operativo.
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.risk_manager import is_session_allowed

def verify_config():
    print("\n" + "="*70)
    print("  VERIFICACION DE CONFIGURACION - ORDER BLOCK BOT")
    print("="*70)
    
    # 1. Verificar sesiones
    print("\n📅 SESIONES CONFIGURADAS:")
    sessions = DEFAULT_PARAMS.get("sessions", {})
    for name, sess in sessions.items():
        print(f"  {name.upper()}:")
        print(f"    Inicio: {sess['start']} UTC")
        print(f"    Fin: {sess['end']} UTC")
        print(f"    Skip: {sess['skip_minutes']} minutos")
        
        # Calcular inicio efectivo
        h_start, m_start = sess['start'].split(':')
        skip_min = sess['skip_minutes']
        total_min = int(h_start) * 60 + int(m_start) + skip_min
        effective_h = total_min // 60
        effective_m = total_min % 60
        print(f"    Inicio efectivo: {effective_h:02d}:{effective_m:02d} UTC (después del skip)")
        
        # Calcular duración
        h_end, m_end = sess['end'].split(':')
        duration = (int(h_end) * 60 + int(m_end)) - (effective_h * 60 + effective_m)
        print(f"    Duración: {duration / 60:.2f} horas")
    
    # 2. Verificar parámetros clave
    print("\n⚙️  PARAMETROS CLAVE:")
    print(f"  Risk per trade: {DEFAULT_PARAMS['risk_per_trade_pct']:.2%}")
    print(f"  Target R:R: 1:{DEFAULT_PARAMS['target_rr']}")
    print(f"  Buffer SL: {DEFAULT_PARAMS['buffer_points']} puntos")
    print(f"  Max trades simultáneos: {DEFAULT_PARAMS['max_simultaneous_trades']}")
    print(f"  Consecutive candles: {DEFAULT_PARAMS['consecutive_candles']}")
    print(f"  BOS filter: {'✅ ACTIVO' if DEFAULT_PARAMS['require_bos'] else '❌ DESACTIVADO'}")
    print(f"  Rejection filter: {'✅ ACTIVO' if DEFAULT_PARAMS['require_rejection'] else '❌ DESACTIVADO'}")
    
    # 3. Verificar estado actual
    print("\n🕐 ESTADO ACTUAL:")
    now = datetime.now(timezone.utc)
    print(f"  Hora UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Día: {now.strftime('%A')}")
    
    is_allowed = is_session_allowed(now, DEFAULT_PARAMS)
    if is_allowed:
        print(f"  Trading: ✅ PERMITIDO (dentro de sesión)")
    else:
        print(f"  Trading: ❌ NO PERMITIDO (fuera de sesión)")
        
        # Calcular próxima sesión
        for name, sess in sessions.items():
            h_start, m_start = sess['start'].split(':')
            skip_min = sess['skip_minutes']
            total_min = int(h_start) * 60 + int(m_start) + skip_min
            next_start_h = total_min // 60
            next_start_m = total_min % 60
            print(f"  Próxima sesión: {next_start_h:02d}:{next_start_m:02d} UTC")
    
    # 4. Verificar archivos críticos
    print("\n📁 ARCHIVOS CRITICOS:")
    files_to_check = [
        "strategies/order_block/backtest/config.py",
        "strategies/order_block/live/trading_bot.py",
        "strategies/order_block/live/run_bot.py",
        "strategies/order_block/live/data_feed.py",
        "strategies/order_block/live/ob_monitor.py",
        "strategies/order_block/live/order_executor.py",
        "strategies/order_block/live/risk_manager.py",
        "strategies/order_block/live/monitor.py",
    ]
    
    all_ok = True
    for file_path in files_to_check:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - NO ENCONTRADO")
            all_ok = False
    
    # 5. Verificar logs
    print("\n📝 LOGS:")
    logs_dir = Path("logs_ob")
    if logs_dir.exists():
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        log_files = [
            f"bot_{today}.log",
            f"trades_{today}.csv",
            f"errors_{today}.log",
        ]
        for log_file in log_files:
            log_path = logs_dir / log_file
            if log_path.exists():
                size = log_path.stat().st_size
                print(f"  ✅ {log_file} ({size} bytes)")
            else:
                print(f"  ⚠️  {log_file} - No creado aún (normal si no hay actividad)")
    else:
        print(f"  ⚠️  Directorio logs_ob no existe")
    
    # Resumen final
    print("\n" + "="*70)
    if all_ok and sessions:
        print("  ✅ VERIFICACION COMPLETA - TODO OK")
        print(f"  Bot configurado para operar: {', '.join(sessions.keys()).upper()}")
        print(f"  Horario: {list(sessions.values())[0]['start']} - {list(sessions.values())[0]['end']} UTC")
    else:
        print("  ⚠️  VERIFICACION COMPLETA - REVISAR ADVERTENCIAS")
    print("="*70 + "\n")

if __name__ == "__main__":
    verify_config()
