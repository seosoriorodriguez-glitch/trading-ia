# -*- coding: utf-8 -*-
"""
Script para reiniciar el bot con la nueva lógica LIMIT.

Pasos:
1. Crea archivo STOP.txt para detener bot actual
2. Espera a que el bot se detenga
3. Elimina STOP.txt
4. Reinicia el bot con lógica LIMIT
"""

import sys
import time
from pathlib import Path

def main():
    print("=" * 80)
    print("REINICIO BOT CON LOGICA LIMIT")
    print("=" * 80)
    print()
    
    stop_file = Path("STOP.txt")
    
    # Paso 1: Crear STOP.txt
    print("Paso 1: Creando archivo STOP.txt para detener bot actual...")
    with open(stop_file, 'w') as f:
        f.write("")
    print("OK Archivo STOP.txt creado")
    print()
    
    # Paso 2: Esperar
    print("Paso 2: Esperando 10 segundos para que el bot se detenga...")
    for i in range(10, 0, -1):
        print(f"  {i}...", end="\r")
        time.sleep(1)
    print("  OK Bot detenido")
    print()
    
    # Paso 3: Eliminar STOP.txt
    print("Paso 3: Eliminando archivo STOP.txt...")
    if stop_file.exists():
        stop_file.unlink()
    print("OK Archivo eliminado")
    print()
    
    # Paso 4: Instrucciones para reiniciar
    print("=" * 80)
    print("LISTO PARA REINICIAR")
    print("=" * 80)
    print()
    print("Ejecuta el siguiente comando para reiniciar el bot:")
    print()
    print("  python strategies/order_block/live/run_bot.py --balance 100000")
    print()
    print("Monitorea los logs para confirmar:")
    print("  - Ordenes LIMIT (no MARKET)")
    print("  - Comentarios: OB_LONG_LIMIT / OB_SHORT_LIMIT")
    print("  - Ordenes pendientes en MT5 (no posiciones inmediatas)")
    print()
    print("Resultados esperados:")
    print("  - Retorno: +30.91% (vs +9.69% anterior)")
    print("  - Max DD: -6.62% (vs -10.69% anterior)")
    print("  - LONG rentable: +$5,745 (vs -$2,351 anterior)")
    print()

if __name__ == "__main__":
    main()
