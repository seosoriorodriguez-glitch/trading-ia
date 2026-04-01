# Trading Journal - Order Block Strategy

Cada trade va en su propia carpeta dentro de `trades/`.

## Estructura por trade

```
trades/
  winners/
    2026-04-01_001_LONG_US30/
      setup.png        <- chart M5 con el OB marcado
      result.png       <- resultado final
      trade.md         <- ficha del trade
  losers/
    2026-04-01_003_SHORT_US30/
      setup.png
      result.png
      trade.md
```

## Nomenclatura de carpetas

`YYYY-MM-DD_NNN_LONG/SHORT_SIMBOLO`

- `NNN` = número correlativo del día (001, 002...)
- Ejemplo: `2026-04-01_001_LONG_US30`
- Van en `winners/` si TP hit, en `losers/` si SL hit
