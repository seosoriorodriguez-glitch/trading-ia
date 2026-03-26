"""
Verificación de conexión a MT5.
Ejecutar ANTES de cualquier backtest o trading.

Uso:
  python verify_mt5.py
  python verify_mt5.py --search US30
  python verify_mt5.py --search GBPJPY
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.config_loader import get_config
from core.market_data import MT5Connection


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verificar conexión MT5")
    parser.add_argument("--search", nargs="*", help="Buscar símbolos (ej: --search US30 GBPJPY NAS)")
    args = parser.parse_args()

    config = get_config()
    mt5_config = config.strategy.get("mt5", {})

    print("=" * 60)
    print("  VERIFICACIÓN DE CONEXIÓN MT5")
    print("=" * 60)
    print(f"\nHost: {mt5_config.get('host', 'localhost')}")
    print(f"Port: {mt5_config.get('port', 8001)}")

    # --- Conectar ---
    mt5 = MT5Connection(
        host=mt5_config.get("host", "localhost"),
        port=mt5_config.get("port", 8001),
    )

    print("\nConectando...")
    if not mt5.connect():
        print("\n❌ NO SE PUDO CONECTAR A MT5")
        print("\nVerifica que:")
        print("  1. Docker está corriendo: docker ps")
        print("  2. El contenedor MT5 está activo: docker-compose up -d")
        print("  3. MT5 está logueado en el contenedor (acceder via VNC)")
        print("  4. Algo Trading está habilitado en MT5")
        sys.exit(1)

    print(f"✅ Conectado — Plataforma: {mt5._platform}")

    # --- Info de cuenta ---
    print(f"\n{'─' * 40}")
    print("CUENTA:")
    print(f"{'─' * 40}")
    account = mt5.get_account_info()
    if account:
        for key, val in account.items():
            if isinstance(val, float):
                print(f"  {key:20s}: {val:>12,.2f}")
            else:
                print(f"  {key:20s}: {val}")
    else:
        print("  ⚠️ No se pudo obtener info de cuenta")

    # --- Buscar símbolos ---
    search_terms = args.search or ["US30", "NAS100", "SPX500", "GBPJPY", "DJI", "DOW"]

    print(f"\n{'─' * 40}")
    print("BÚSQUEDA DE SÍMBOLOS:")
    print(f"{'─' * 40}")

    _mt5 = mt5._mt5

    for term in search_terms:
        print(f"\n  Buscando '{term}'...")

        # Intentar obtener info directamente
        if hasattr(_mt5, 'symbols_get'):
            # Librería oficial (Windows) o silicon con symbols_get
            try:
                symbols = _mt5.symbols_get(group=f"*{term}*")
                if symbols:
                    for s in symbols[:10]:  # Máximo 10 resultados
                        print(f"    📌 {s.name:25s} | Descripción: {getattr(s, 'description', 'N/A')}")
                else:
                    # Intentar nombre exacto
                    info = mt5.get_symbol_info(term)
                    if info:
                        print(f"    📌 {term} encontrado — {info}")
                    else:
                        print(f"    ❌ No encontrado")
            except Exception as e:
                print(f"    ⚠️ Error buscando: {e}")
                # Fallback: intentar nombre directo
                info = mt5.get_symbol_info(term)
                if info:
                    print(f"    📌 {term} encontrado")
                    for k, v in info.items():
                        print(f"        {k}: {v}")
                else:
                    print(f"    ❌ '{term}' no encontrado como símbolo directo")
        else:
            # silicon-metatrader5 puede no tener symbols_get
            info = mt5.get_symbol_info(term)
            if info:
                print(f"    📌 {term} encontrado")
                for k, v in info.items():
                    print(f"        {k}: {v}")
            else:
                # Probar variantes comunes
                variants = [
                    term, f"{term}.raw", f"{term}Cash", f"{term}_raw",
                    term.upper(), term.lower(),
                ]
                found = False
                for variant in variants:
                    info = mt5.get_symbol_info(variant)
                    if info:
                        print(f"    📌 Encontrado como: {variant}")
                        for k, v in info.items():
                            print(f"        {k}: {v}")
                        found = True
                        break
                if not found:
                    print(f"    ❌ No encontrado (intenté: {', '.join(variants)})")

    # --- Verificar instrumentos configurados ---
    print(f"\n{'─' * 40}")
    print("INSTRUMENTOS CONFIGURADOS vs MT5:")
    print(f"{'─' * 40}")

    for name, inst in config.get_enabled_instruments().items():
        symbol = inst["symbol_mt5"]
        info = mt5.get_symbol_info(symbol)
        if info:
            print(f"\n  ✅ {name} → {symbol}")
            print(f"     Point:         {info.get('point', 'N/A')}")
            print(f"     Digits:        {info.get('digits', 'N/A')}")
            print(f"     Contract size: {info.get('contract_size', 'N/A')}")
            print(f"     Vol min:       {info.get('volume_min', 'N/A')}")
            print(f"     Vol step:      {info.get('volume_step', 'N/A')}")
            print(f"     Spread:        {info.get('spread', 'N/A')}")
        else:
            print(f"\n  ❌ {name} → '{symbol}' NO ENCONTRADO EN MT5")
            print(f"     Actualiza symbol_mt5 en config/instruments.yaml")

    # --- Test de datos históricos ---
    print(f"\n{'─' * 40}")
    print("TEST DE DATOS HISTÓRICOS:")
    print(f"{'─' * 40}")

    for name, inst in config.get_enabled_instruments().items():
        symbol = inst["symbol_mt5"]
        try:
            candles_h4 = mt5.get_candles(symbol, "H4", 10)
            candles_h1 = mt5.get_candles(symbol, "H1", 10)

            if candles_h4 and candles_h1:
                print(f"\n  ✅ {name} ({symbol})")
                print(f"     H4: {len(candles_h4)} velas | "
                      f"Última: {candles_h4[-1].time} | "
                      f"Close: {candles_h4[-1].close}")
                print(f"     H1: {len(candles_h1)} velas | "
                      f"Última: {candles_h1[-1].time} | "
                      f"Close: {candles_h1[-1].close}")
            else:
                print(f"\n  ⚠️ {name}: No se obtuvieron velas")
        except Exception as e:
            print(f"\n  ❌ {name}: Error obteniendo datos — {e}")

    # --- Desconectar ---
    mt5.disconnect()

    print(f"\n{'=' * 60}")
    print("  VERIFICACIÓN COMPLETADA")
    print(f"{'=' * 60}")
    print("\nSi todos los instrumentos están ✅, puedes proceder a:")
    print("  python prepare_data.py --source mt5 --instrument US30 --days 730")
    print("  python run_backtest.py --data-h1 data/US30_H1.csv --data-h4 data/US30_H4.csv --instrument US30 --output data/backtest_US30.csv")


if __name__ == "__main__":
    main()
