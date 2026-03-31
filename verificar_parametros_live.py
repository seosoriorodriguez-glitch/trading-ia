# -*- coding: utf-8 -*-
"""
Verificar que el bot live está usando los parámetros optimizados
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from strategies.order_block.backtest.config import DEFAULT_PARAMS

print("\n" + "="*80)
print("  VERIFICACIÓN: Parámetros del Live Bot")
print("="*80)

print("\n📋 PARÁMETROS ACTUALES:")

print(f"\n🎯 Risk Management:")
print(f"  target_rr:        {DEFAULT_PARAMS['target_rr']} {'✅ CORRECTO' if DEFAULT_PARAMS['target_rr'] == 3.5 else '❌ INCORRECTO (debe ser 3.5)'}")
print(f"  buffer_points:    {DEFAULT_PARAMS['buffer_points']} {'✅ CORRECTO' if DEFAULT_PARAMS['buffer_points'] == 25 else '❌ INCORRECTO (debe ser 25)'}")
print(f"  min_risk_points:  {DEFAULT_PARAMS['min_risk_points']}")
print(f"  max_risk_points:  {DEFAULT_PARAMS['max_risk_points']}")
print(f"  min_rr_ratio:     {DEFAULT_PARAMS['min_rr_ratio']}")

print(f"\n🕐 Sesión:")
ny_session = DEFAULT_PARAMS['sessions']['new_york']
print(f"  Inicio:           {ny_session['start']} UTC")
print(f"  Fin:              {ny_session['end']} UTC")
print(f"  Skip minutos:     {ny_session['skip_minutes']}")
print(f"  Trading real:     13:45-20:00 UTC")

print(f"\n🔍 Filtros:")
print(f"  require_bos:      {DEFAULT_PARAMS['require_bos']} {'✅ CORRECTO (False)' if not DEFAULT_PARAMS['require_bos'] else '❌ INCORRECTO (debe ser False)'}")
print(f"  require_rejection: {DEFAULT_PARAMS['require_rejection']}")
print(f"  ema_trend_filter: {DEFAULT_PARAMS['ema_trend_filter']}")

print(f"\n💰 Trading:")
print(f"  risk_per_trade:   {DEFAULT_PARAMS['risk_per_trade_pct']*100:.2f}%")
print(f"  max_trades:       {DEFAULT_PARAMS['max_simultaneous_trades']}")

print("\n" + "="*80)
print("  RESULTADOS ESPERADOS (Backtest 104 días)")
print("="*80)

print(f"\n📊 Con estos parámetros:")
print(f"  Retorno:          +30.91%")
print(f"  Win Rate:         29.4%")
print(f"  Max DD:           6.62%")
print(f"  Profit Factor:    1.36")
print(f"  Trades:           ~197 (104 días)")
print(f"  Frecuencia:       ~2 trades/día")
print(f"  Avg Win:          $2,017")
print(f"  Avg Loss:         $-619")

print("\n" + "="*80)
print("  ESTADO")
print("="*80)

# Verificar que todos los parámetros críticos son correctos
all_correct = (
    DEFAULT_PARAMS['target_rr'] == 3.5 and
    DEFAULT_PARAMS['buffer_points'] == 25 and
    DEFAULT_PARAMS['require_bos'] == False
)

if all_correct:
    print(f"\n  ✅ TODOS LOS PARÁMETROS CORRECTOS")
    print(f"  ✅ Bot configurado con parámetros optimizados")
    print(f"  ✅ Listo para operar")
else:
    print(f"\n  ❌ ALGUNOS PARÁMETROS INCORRECTOS")
    print(f"  ⚠️  Revisar configuración")

print("\n" + "="*80)
