# Bot S/R Pivot al toque H1

Bot nuevo, en carpeta propia. No comparte archivos con los bots activos (OB London, London 1%, Darwinex) ni con los
módulos de `strategies/order_block/`.

## Qué hace
- **Niveles:** pivotes H1 del indicador LuxAlgo "Support and Resistance Levels with Breaks" (15 velas a cada lado).
  Un nivel se puede operar desde la apertura de la vela H1 número 16 después del pivote. Siempre hay 5 niveles vivos.
- **Órdenes:**
  - Soporte → BUY LIMIT 20 pts sobre el nivel.
  - Resistencia → SELL LIMIT 20 pts bajo el nivel.
  - SL a 130 pts al otro lado del nivel; TP 2.5R.
  - Los 20 y 130 pts son a precio 47 000 y se escalan con el precio: hoy son ~22 y ~143.
- **Reglas:**
  - La orden se pone solo si el precio está del lado de afuera.
  - Cada nivel se opera una sola vez.
  - Una posición a la vez.
  - Sin entradas de 08:26 a 08:34 hora de Nueva York.
  - Cierra todo el viernes a las 19:00 UTC.
  - Opera las 24 h de lunes a viernes.
- **Riesgo:** `riesgo_fijo` en dinero por trade (Darwinex: $500, igual que el OB) o `riesgo_pct` del balance.
- **Magic:** 345690. Solo toca sus propias órdenes y posiciones, así que puede compartir terminal con otro bot.

Resultado del backtest (velas M1 de FTMO, swap supuesto de −8 pts por noche en compras y −2 en ventas):

| | Total | Peor caída |
|---|---|---|
| 2025 | +16.6R | 15.7R |
| 2026 (ene–oct) | +61.6R | 8.1R |

2020-2024 (solo informativo): +50.6R, 4 de 5 años positivos.

## Comprobado antes de usarlo
| Prueba | Qué mide | Resultado |
|---|---|---|
| `herramientas/paridad.py` | La lógica del bot contra el backtest, minuto a minuto | 2025: 192/192 trades idénticos · 2026: 163/163 |
| `herramientas/simulacro.py` | El bot entero (`bot.py`) contra un MT5 falso con las velas históricas | 2025: 192/192 · 2026: 161 + 2 descartados a propósito |

Los 2 descartados de 2026 son lunes en que el precio abrió más allá del SL: el backtest los anotaba como −0.01R y el
bot no entra.

Arreglos de la auditoría del 10-nov-2026 (ver `papel/README.md`). Las paridades y el simulacro se corren sin feriados,
con la regla de la investigación. Resultados después de los arreglos:

| Prueba | Antes | Ahora |
|---|---|---|
| Arrancar con el backtest en posición (12 casos, mar-abr 2026) | repetía el nivel 12 de 12 | 0 de 12 |
| Bot llamado en cada tick (sep-2026) | 15/16 | 16/16, sin entradas en el minuto del cierre |
| Caída del VPS de viernes a lunes (sep-2026) | 15/16, −3.6R contra +1.8R | 16/16 |
| Simulacro modo real (jul-oct 2026) | — | 64/64 |
| Calendario de feriados 2025-26 | — | cambia 1 trade (19-06-2026) |

Diferencia conocida con el backtest: si al abrir un minuto el precio ya pasó la orden, el bot entra a mercado con el
mismo SL y TP. Es lo que hace el backtest, que la llena en la apertura como si la límite ya hubiera estado puesta.

## Modo papel (la prueba de 1-2 meses, sin abrir cuentas)
Se conecta a una terminal que ya existe (por ejemplo la de Darwinex, que lee WS30 en vivo) y **no envía ninguna
orden**:
- Las órdenes y la posición son virtuales y se llenan con cada tick real del bróker (bid/ask), no con una mirada
  cada 2 segundos.
- El swap se descuenta en cada medianoche del servidor con los datos reales del símbolo (largo/corto, modo de
  cálculo y día triple).
- No toca la cuenta ni el DARWIN, y puede leer la misma terminal que el bot OB, como hace el collector del panel.
- Si se apaga y se vuelve a lanzar, procesa los ticks del tiempo apagado: en la realidad las órdenes habrían
  quedado puestas en el servidor.

```
python papel/estrategias/sr_pivot_h1/run_bot.py --config papel/estrategias/sr_pivot_h1/config/darwinex.yaml --papel
```

**Archivos** (en `logs_sr_pivot/papel_<login>/`):
- `trades.csv`: con R bruto, R neto (con swap y comisión), noches y swap en puntos.
- `eventos.log`.
- `papel_estado.json`: órdenes, posición y balance virtuales.

Prueba sin conexión: `herramientas/prueba_papel.py` alimenta el bot con ticks armados desde velas M1. En septiembre
de 2026 coinciden las 16 entradas y salidas con el backtest. El R difiere un poco porque los ticks de prueba saltan
directo al máximo y al mínimo de cada vela.

Lo que el modo papel NO prueba es la ejecución real (aceptación de órdenes, deslizamiento, valor por punto). Se
confirma con los primeros trades reales; el bot avisa si el valor por punto no cuadra.

## Prueba de 1-2 meses en otro MT5 (alternativa con cuenta demo)
1. Instalar un MT5 aparte (por ejemplo `C:\Program Files\MT5_SR_DEMO\`) y entrar con la cuenta de prueba. Lo ideal
   es una demo de Darwinex, porque tiene el mismo WS30, spread y swap.
2. Revisar los costos del símbolo. Este paso no envía órdenes:
   ```
   python papel/estrategias/sr_pivot_h1/herramientas/costos_broker.py --terminal "C:\Program Files\MT5_SR_DEMO\terminal64.exe" --simbolo WS30
   ```
3. Completar `config/demo.yaml`: `terminal`, `simbolo` (`WS30` o `US30.cash`) y `balance_esperado`.
4. Ver qué haría sin operar:
   ```
   python papel/estrategias/sr_pivot_h1/run_bot.py --config papel/estrategias/sr_pivot_h1/config/demo.yaml --dry-run
   ```
   Muestra los 5 niveles activos y las órdenes que pondría.
5. Operar:
   ```
   python papel/estrategias/sr_pivot_h1/run_bot.py --config papel/estrategias/sr_pivot_h1/config/demo.yaml
   ```
6. **Primer trade:** si en `eventos.log` aparece `OJO valor por punto`, el riesgo real no es el configurado. Hay que
   ajustar `valor_punto_lote`. En Darwinex WS30, MT5 informa 0.1 pero la P&L real es ~1.0.

**Para detenerlo:** crear `STOP_SR_PIVOT.txt` en la raíz del proyecto. El bot cancela sus órdenes pendientes y sale;
la posición abierta queda con su SL y TP. Borrar el archivo antes de volver a lanzarlo.

**Archivos** (en `logs_sr_pivot/<login>/`):
- `eventos.log`: todo lo que hizo.
- `trades.csv`: un trade por fila, con R y el valor por punto observado.
- `estado.json`: los niveles ya usados. Si se pierde, se reconstruye desde el historial de MT5.

Después de la prueba se compara `trades.csv` con el backtest del mismo período corrido con las velas de ese broker.

## Darwinex (cuenta real desde el 13-nov-2026)
El usuario decidió pasarla a real sin esperar los 2 meses de papel, junto con la falsa ruptura. El papel sigue corriendo
para comparar.

`config/darwinex.yaml` apunta al mismo terminal que el bot OB Darwinex (`MT5_BREAKERBLOCKS`), con `WS30` y
`valor_punto_lote: 1.0`. La cuenta es **Hedge**, así que los bots no se pisan. Pero **todo lo que opera esa cuenta forma
el mismo DARWIN (YGZY)**; para un DARWIN aparte hace falta otra cuenta de Darwinex.

**Riesgo:** `riesgo_fijo: 500`, $500 fijos por trade. Es lo mismo que arriesga el OB de Darwinex: su config dice 0.05 %,
pero con el valor por punto real de WS30 son ~$500 (13-nov: −$484 a −$528 por SL).

**Margen:** la posición S/R (~3.3 lotes, unos $9k), la de la falsa ruptura (~1.9 lotes, ~$5k) y las 2 del OB
(~9 lotes cada una) caben juntas en los ~$108k de la cuenta.

**Gap que llena dos órdenes a la vez** (13-nov-2026). MT5 llena todas las LIMIT cruzadas; el backtest, solo la más
cercana a la apertura.
- El bot se queda con esa y cierra las demás a mercado.
- Los niveles cerrados quedan sin usar, como en el backtest.

Simulacro `--todas`: 2025 192/192 trades idénticos, con 1 llenado de más cerrado al minuto siguiente (+0.06R). En
2026, 160/163, las mismas 3 diferencias de siempre:
- 2 lunes que abrieron más allá del SL;
- el 19-06, Juneteenth sin feriados.

**Lanzarlo en el VPS** (desde `C:\Users\Administrator\trading-ia`, después de `git pull`):
```
python papel/estrategias/sr_pivot_h1/run_bot.py --config papel/estrategias/sr_pivot_h1/config/darwinex.yaml --dry-run
python papel/estrategias/sr_pivot_h1/run_bot.py --config papel/estrategias/sr_pivot_h1/config/darwinex.yaml
```
