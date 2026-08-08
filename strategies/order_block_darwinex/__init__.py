# -*- coding: utf-8 -*-
"""
Order Block DARWINEX — copia independiente de la estrategia Order Block London,
dedicada EXCLUSIVAMENTE a la cuenta Darwinex Zero (simbolo WS30).

Esta carpeta es 100% aditiva e independiente: NO comparte ningun archivo con
`order_block_london` (FTMO). Tocar/editar aqui NO afecta a los bots FTMO.

Diferencias vs FTMO (order_block_london):
  - Simbolo:   WS30 (Dow Jones en Darwinex)  vs  US30.cash (FTMO)
  - Terminal:  MT5_BREAKERBLOCKS             vs  MT5_BTCUSD / MT5_US30
  - Magic:     345681                        vs  345680
  - Valor pt:  $0.1/punto (leido de MT5)     vs  $1/punto
  - Leverage:  20:1 (ESMA)                   vs  ~100:1 (FTMO)
  - STOP file: STOP_DARWINEX.txt             vs  STOP_LONDON.txt
  - Logs:      logs_darwinex/                vs  logs_ob/
"""
