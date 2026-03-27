# -*- coding: utf-8 -*-
"""
Script principal para ejecutar el bot de trading en vivo
"""
import sys
import io
import argparse
from pathlib import Path

# Fix encoding para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.pivot_scalping.live.trading_bot import TradingBot


def main():
    parser = argparse.ArgumentParser(description='FTMO Trading Bot - Pivot Scalping')
    
    parser.add_argument(
        '--symbol',
        type=str,
        default='US30.cash',
        help='Símbolo a operar (default: US30.cash)'
    )
    
    parser.add_argument(
        '--balance',
        type=float,
        default=100000,
        help='Balance inicial (default: 100000)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo dry-run (simula sin ejecutar órdenes reales)'
    )
    
    parser.add_argument(
        '--strategy',
        type=str,
        default='strategies/pivot_scalping/config/scalping_params_M5M1_aggressive.yaml',
        help='Path al config de estrategia'
    )
    
    parser.add_argument(
        '--ftmo-config',
        type=str,
        default='strategies/pivot_scalping/config/ftmo_rules.yaml',
        help='Path al config de FTMO'
    )
    
    parser.add_argument(
        '--telegram-token',
        type=str,
        default='8577007615:AAHy31IegzvbezCpyNfIlaZh_IsKuV-4M9A',
        help='Token del bot de Telegram'
    )
    
    parser.add_argument(
        '--telegram-chat-id',
        type=str,
        default='6265548967',
        help='Chat ID de Telegram'
    )
    
    parser.add_argument(
        '--no-telegram',
        action='store_true',
        help='Desactivar notificaciones de Telegram'
    )
    
    args = parser.parse_args()
    
    try:
        # Telegram
        telegram_token = None if args.no_telegram else args.telegram_token
        telegram_chat_id = None if args.no_telegram else args.telegram_chat_id
        
        # Crear bot
        print("🔧 Inicializando módulos...", flush=True)
        bot = TradingBot(
            symbol=args.symbol,
            strategy_config_path=args.strategy,
            ftmo_config_path=args.ftmo_config,
            initial_balance=args.balance,
            dry_run=args.dry_run,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id
        )
        
        # Iniciar
        print("=" * 60, flush=True)
        print("🤖 FTMO TRADING BOT - PIVOT SCALPING", flush=True)
        print("=" * 60, flush=True)
        print(f"Símbolo: {args.symbol}", flush=True)
        print(f"Balance: ${args.balance:,.2f}", flush=True)
        print(f"Estrategia: M5/M1 Agresiva", flush=True)
        print(f"Modo: {'DRY RUN' if args.dry_run else 'LIVE'}", flush=True)
        print(f"Telegram: {'Activado' if not args.no_telegram else 'Desactivado'}", flush=True)
        print("=" * 60, flush=True)
        print(flush=True)
        
        bot.start()
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
