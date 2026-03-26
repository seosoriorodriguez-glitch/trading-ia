#!/usr/bin/env python3
"""
Script para ejecutar múltiples backtests en paralelo.

Permite probar diferentes estrategias, timeframes e instrumentos
sin modificar la configuración base.

Uso:
    python run_parallel_backtests.py --all
    python run_parallel_backtests.py --strategy h4_h1 --instruments US30 NAS100
    python run_parallel_backtests.py --strategy h1_m15 --instruments US30
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json

# Configuración de estrategias disponibles
STRATEGIES = {
    "h4_h1": {
        "name": "H4 Zonas + H1 Señales (Base)",
        "config": "config/strategy_params.yaml",
        "instruments_config": "config/instruments.yaml",
        "zone_tf": "H4",
        "signal_tf": "H1",
        "description": "Estrategia base validada - PF 3.57, WR 72%"
    },
    "h1_m15": {
        "name": "H1 Zonas + M15 Señales (Experimental)",
        "config": "config/strategy_params_h1_m15.yaml",
        "instruments_config": "config/instruments_h1_m15.yaml",
        "zone_tf": "H1",
        "signal_tf": "M15",
        "description": "Timeframes menores - Mayor frecuencia, más riesgo"
    }
}

INSTRUMENTS = {
    "US30": {"ticker": "^DJI", "name": "Dow Jones"},
    "NAS100": {"ticker": "^IXIC", "name": "Nasdaq 100"},
    "SPX500": {"ticker": "^GSPC", "name": "S&P 500"},
}


def download_data(ticker, days, output_name):
    """Descarga datos de Yahoo Finance."""
    print(f"\n📥 Descargando {output_name}...")
    cmd = [
        "python3", "download_yahoo_data.py",
        "--ticker", ticker,
        "--days", str(days),
        "--output", output_name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error descargando {output_name}")
        print(result.stderr)
        return False
    
    print(f"✅ {output_name} descargado")
    return True


def run_backtest(strategy_key, instrument, balance=100000):
    """Ejecuta un backtest para una estrategia e instrumento."""
    strategy = STRATEGIES[strategy_key]
    inst_info = INSTRUMENTS[instrument]
    
    # Nombres de archivos de datos
    zone_tf = strategy["zone_tf"]
    signal_tf = strategy["signal_tf"]
    
    data_h1 = f"data/{instrument}_{signal_tf}_730d.csv"
    data_h4 = f"data/{instrument}_{zone_tf}_730d.csv"
    
    # Verificar que los datos existan
    if not Path(data_h1).exists() or not Path(data_h4).exists():
        print(f"⚠️  Datos no encontrados para {instrument} ({strategy_key})")
        print(f"   Esperado: {data_h1} y {data_h4}")
        return None
    
    # Nombre de archivo de salida
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = f"data/backtest_{instrument}_{strategy_key}_{timestamp}.csv"
    
    print(f"\n🔄 Ejecutando backtest: {inst_info['name']} - {strategy['name']}")
    
    # Ejecutar backtest
    cmd = [
        "python3", "-B", "run_backtest.py",
        "--data-h1", data_h1,
        "--data-h4", data_h4,
        "--instrument", instrument,
        "--balance", str(balance),
        "--output", output,
        "--config", strategy["config"]
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error en backtest {instrument} - {strategy_key}")
        print(result.stderr)
        return None
    
    # Extraer métricas del output
    lines = result.stdout.split('\n')
    metrics = {}
    
    for line in lines:
        if "Balance final:" in line:
            metrics["balance_final"] = line.split("$")[1].split()[0].replace(",", "")
        elif "Retorno total:" in line:
            metrics["retorno"] = line.split(":")[1].strip()
        elif "Profit Factor (USD):" in line:
            metrics["profit_factor"] = line.split(":")[1].split()[0]
        elif "Total operaciones:" in line:
            metrics["trades"] = line.split(":")[1].strip()
        elif "Ganadoras:" in line:
            parts = line.split(":")
            if len(parts) > 1:
                metrics["win_rate"] = parts[1].split("(")[1].split(")")[0]
        elif "Max Drawdown:" in line:
            metrics["max_dd"] = line.split(":")[1].strip()
    
    print(f"✅ Backtest completado: {output}")
    print(f"   Balance: ${metrics.get('balance_final', 'N/A')}")
    print(f"   Retorno: {metrics.get('retorno', 'N/A')}")
    print(f"   PF: {metrics.get('profit_factor', 'N/A')}")
    print(f"   Trades: {metrics.get('trades', 'N/A')}")
    print(f"   WR: {metrics.get('win_rate', 'N/A')}")
    print(f"   Max DD: {metrics.get('max_dd', 'N/A')}")
    
    return {
        "strategy": strategy_key,
        "instrument": instrument,
        "output_file": output,
        "metrics": metrics,
        "timestamp": timestamp
    }


def main():
    parser = argparse.ArgumentParser(
        description="Ejecutar backtests en paralelo para múltiples estrategias e instrumentos"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ejecutar todos los backtests (todas las estrategias y todos los instrumentos)"
    )
    
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGIES.keys()),
        help="Estrategia a probar"
    )
    
    parser.add_argument(
        "--instruments",
        nargs="+",
        choices=list(INSTRUMENTS.keys()),
        help="Instrumentos a probar"
    )
    
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Solo descargar datos, no ejecutar backtests"
    )
    
    parser.add_argument(
        "--balance",
        type=int,
        default=100000,
        help="Balance inicial (default: 100000)"
    )
    
    args = parser.parse_args()
    
    # Determinar qué ejecutar
    if args.all:
        strategies_to_run = list(STRATEGIES.keys())
        instruments_to_run = list(INSTRUMENTS.keys())
    else:
        if not args.strategy or not args.instruments:
            parser.error("Debes especificar --strategy e --instruments, o usar --all")
        strategies_to_run = [args.strategy]
        instruments_to_run = args.instruments
    
    print("=" * 60)
    print("BACKTESTS EN PARALELO")
    print("=" * 60)
    print(f"\nEstrategias: {', '.join(strategies_to_run)}")
    print(f"Instrumentos: {', '.join(instruments_to_run)}")
    print(f"Balance inicial: ${args.balance:,}")
    print()
    
    # Descargar datos necesarios
    print("=" * 60)
    print("DESCARGA DE DATOS")
    print("=" * 60)
    
    for instrument in instruments_to_run:
        ticker = INSTRUMENTS[instrument]["ticker"]
        
        # Descargar para cada estrategia (diferentes timeframes)
        for strategy_key in strategies_to_run:
            strategy = STRATEGIES[strategy_key]
            
            # Descargar datos de zona
            zone_output = f"{instrument}_{strategy['zone_tf']}"
            if not Path(f"data/{zone_output}_730d.csv").exists():
                download_data(ticker, 730, zone_output)
            
            # Descargar datos de señal (si es diferente)
            if strategy['signal_tf'] != strategy['zone_tf']:
                signal_output = f"{instrument}_{strategy['signal_tf']}"
                if not Path(f"data/{signal_output}_730d.csv").exists():
                    download_data(ticker, 730, signal_output)
    
    if args.download_only:
        print("\n✅ Descarga completada")
        return
    
    # Ejecutar backtests
    print("\n" + "=" * 60)
    print("EJECUCIÓN DE BACKTESTS")
    print("=" * 60)
    
    results = []
    
    for strategy_key in strategies_to_run:
        for instrument in instruments_to_run:
            result = run_backtest(strategy_key, instrument, args.balance)
            if result:
                results.append(result)
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    if not results:
        print("❌ No se completaron backtests")
        return
    
    # Agrupar por estrategia
    for strategy_key in strategies_to_run:
        strategy_results = [r for r in results if r["strategy"] == strategy_key]
        
        if not strategy_results:
            continue
        
        print(f"\n{STRATEGIES[strategy_key]['name']}")
        print("-" * 60)
        
        for result in strategy_results:
            inst = result["instrument"]
            metrics = result["metrics"]
            
            print(f"\n{INSTRUMENTS[inst]['name']} ({inst}):")
            print(f"  Balance: ${metrics.get('balance_final', 'N/A')}")
            print(f"  Retorno: {metrics.get('retorno', 'N/A')}")
            print(f"  PF: {metrics.get('profit_factor', 'N/A')}")
            print(f"  Trades: {metrics.get('trades', 'N/A')}")
            print(f"  WR: {metrics.get('win_rate', 'N/A')}")
            print(f"  Max DD: {metrics.get('max_dd', 'N/A')}")
            print(f"  Archivo: {result['output_file']}")
    
    # Guardar resumen en JSON
    summary_file = f"data/backtest_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "strategies": strategies_to_run,
            "instruments": instruments_to_run,
            "balance": args.balance,
            "results": results
        }, f, indent=2)
    
    print(f"\n📊 Resumen guardado en: {summary_file}")
    print("\n✅ Todos los backtests completados")


if __name__ == "__main__":
    main()
