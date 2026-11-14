# Falsa ruptura de pivotes H1

Corre de dos formas:
- **En papel**, dentro de `papel/runner.py`: usa los precios en vivo de la terminal y sus órdenes son virtuales.
- **En real** desde el 13-nov-2026, con `run_bot.py` y órdenes STOP en MT5 (ver [Cuenta real](#cuenta-real-darwinex)).

Tiene carpeta propia y no toca los bots OB en producción. Del S/R hereda el broker (papel y MT5) y los horarios.

## Qué hace
- **Niveles:** los mismos pivotes H1 15/15 del S/R. Un nivel se puede romper mientras está entre los 5 últimos
  activados.
- **Ruptura:** es la primera vela H1 que **cierra** más allá del nivel, del lado contrario a donde estaba el precio
  cuando el nivel se activó. Cuenta solo la primera: si esa orden no se llena, el nivel queda terminado.
- **Orden:** al cierre de esa vela se pone una STOP **en contra** de la ruptura, a 20 pts del nivel hacia el lado de la
  ruptura. Por ejemplo, si la ruptura es alcista va una VENTA STOP en nivel + 20.
  - Vale 8 h.
  - Se pone solo con el precio del lado de afuera. Si al abrir la vela el precio ya la pasó, entra a mercado.
  - Solo cuentan las últimas 5 órdenes nacidas.
- **SL espejo:** se mide la distancia desde la orden hasta el extremo contrario de las 4 últimas velas H1 (el mínimo, si
  la ruptura es alcista), más 20 pts. El SL se pone a esa misma distancia, del otro lado de la orden. En la práctica
  queda más allá de la punta de la ruptura en el 98 % de los casos. El riesgo mediano es ~270 pts.
- **TP:** 3R.
- **Reglas:**
  - Una posición a la vez.
  - Sin entradas de 08:26 a 08:34 hora de Nueva York.
  - Cierra todo el viernes a las 19:00 UTC.
- **Riesgo:** en papel, 0.5 % de 100 000 virtuales. En real, $500 fijos por trade, igual que el OB de Darwinex.
- **Destino:** Darwinex (WS30).
- Los 20 pts están a precio 47 000 y se escalan con el precio.

Backtest con costos FTMO y swap supuesto (investigación: `research/pa_lab/estructura_pa/falsa_ruptura_v2.py`, base):

| | Trades | Total | Peor caída |
|---|---|---|---|
| 2025 | 76 | +15.4R | 6.2R |
| 2026 (ene–oct) | 67 | +26.7R | 5.1R |
| 2020-2024 (informativo) | 413 | +28.2R | 24.3R |

Cerca del 28 % de los trades cierran por el corte del viernes, así que esa regla importa.

## Calentamiento
Al arrancar, el bot no sabe qué órdenes se habrían operado antes. Por eso corre el mismo backtest sobre el historial M1
reciente del broker y marca como usadas todas las órdenes que esa simulación llenó. Así no se repite el error del S/R
del 10-nov-2026, cuando operó un nivel que ya se había usado. Si el backtest tendría una posición abierta en ese
momento, lo avisa en el log; el papel arranca sin posición.

## Comprobado antes de usarlo
| Prueba | Qué mide | Resultado |
|---|---|---|
| `herramientas/paridad.py` | Lógica del bot (hora a hora, solo con el pasado) contra la investigación | 2026: 156/156 órdenes y 67/67 trades idénticos · 2025: 183/183 y 76/76 |
| `herramientas/prueba_papel.py` | El bot entero en papel con ticks históricos falsos, incluido el calentamiento | may–oct 2026: 43/43 entradas y salidas idénticas (R del papel algo menor: el tick falso llena el SL en el extremo de la vela) · calentamiento: no repite la orden ya operada |
| `papel/prueba_offline.py` | Runner + las dos estrategias + subida al panel (Supabase falso) | filas solo `lab_`, cuentas y tickets virtuales, papel vs backtest 7/7 |

Feriados: desde el 10-nov-2026 el bot y su backtest cortan la semana en su último día con mercado
(`papel/calendario.py`), 15 min antes de un cierre temprano. La investigación cerraba en la última vela de esa semana.
En 2025-2026 eso cambia 1 trade (19-06-2026: +2.4R en vez de +3.0R). Las paridades se miden sin feriados, con la regla
de la investigación.

Arreglos de la auditoría del 10-nov-2026 (ver `papel/README.md`), comprobados con las pruebas del auditor:
- Arranque con el backtest en posición: no opera hasta que esa posición habría cerrado.
- Bot llamado en cada tick: 7/7 en sep-2026.
- Caída del VPS de viernes a lunes: 7/7; antes daba 6/7.

## Cuenta real (Darwinex)
Decidido por el usuario el 13-nov-2026: entra a real junto con el S/R, sin esperar los 2 meses de papel. El papel sigue
corriendo para comparar.

**Qué cambia respecto del papel:**
- `broker_mt5.py`: VENTA STOP / COMPRA STOP en MT5 con magic **345691** y comentario `FR <clave>`.
  - Cada orden va con su vencimiento (8 h) si el símbolo lo acepta; el servidor la borra aunque el bot esté apagado.
  - Si el bróker no acepta la fecha, va GTC y la cancela el bot.
- **Riesgo fijo** `riesgo_fijo: 500` en el config. Con un riesgo típico de 270 pts son ~1.85 lotes.
- **Gap que llena dos STOP a la vez.** MT5 llena todas las cruzadas; el backtest, solo la más cercana a la apertura.
  - El bot se queda con esa y cierra las demás a mercado en el minuto siguiente.
  - Las órdenes cerradas quedan sin usar, como en el backtest.
  - Lo mismo hace el S/R con sus LIMIT.

**Pruebas del modo real** (`herramientas/simulacro.py`: el bot entero contra un MT5 falso, sin feriados):

| | Trades idénticos al backtest | Con `--todas` (MT5 llena todas las cruzadas) |
|---|---|---|
| 2025 | — | 76/76; 3 llenados de más, cerrados al minuto siguiente (−0.09R) |
| 2026 (ene–oct) | 66/67 | 66/67; 4 llenados de más, cerrados al minuto siguiente (−0.02R) |

La diferencia de 2026 es el 19-06 (Juneteenth). El backtest sin feriados no tiene velas después del cierre temprano y
mantiene la posición todo el fin de semana; el bot la cierra el lunes. Con feriados, como corre en real, cierran igual.

Las órdenes que se mandan a MT5 (tipo, precio, SL/TP, vencimiento, magic, comentario, lado del margen) se revisaron
con un MT5 simulado.

**Cómo lanzarlo en el VPS** (desde `C:\Users\Administrator\trading-ia`, después de `git pull`):
```
python papel/estrategias/falsa_ruptura_h1/run_bot.py --config papel/estrategias/falsa_ruptura_h1/config/darwinex.yaml --dry-run
python papel/estrategias/falsa_ruptura_h1/run_bot.py --config papel/estrategias/falsa_ruptura_h1/config/darwinex.yaml
```
- El `--dry-run` muestra la cuenta, el valor por punto, el riesgo y las órdenes que pondría, sin mandar nada.
- **Para detenerlo:** crear `STOP_FALSA_RUPTURA.txt` en la raíz. El bot cancela sus pendientes y sale; la posición
  queda con su SL/TP. Con Ctrl+C las pendientes quedan en MT5 y vencen solas a su hora.
- **Archivos** en `logs_falsa_ruptura/<login>/`: `eventos.log`, `trades.csv` y `estado.json`.
- **Primer trade:** si `eventos.log` dice `OJO valor por punto`, el riesgo real no es $500.

## Auditoría del 14-nov-2026 (antes de operar en real)
Dos revisiones independientes, línea por línea, contra la investigación. **La lógica y los parámetros replican la
investigación**: paridad 2025 y 2026 idéntica en niveles, órdenes, minutos bloqueados y trades. Lo que se arregló es
robustez de la ejecución en MT5 real (vale para el S/R y la falsa ruptura):
- **Reconexión:** si la terminal se reinicia, el bot vuelve a conectar. Antes seguía vivo pero ciego.
- **Vencimiento:** las pendientes vencen en el corte de fin de semana (la falsa ruptura, también a las 8 h). Si el
  bot se cae, no quedan vivas el fin de semana. Si el bróker no acepta la fecha, van GTC.
- **Spread de "del lado de afuera":** se usa el de la vela M1 anterior, como el backtest. En la reapertura de las 01:00
  el spread del tick (10-30 pts) hacía poner compras que el backtest no pone.
- **Orden muy cerca del precio:** si el bróker no la deja poner (distancia mínima) o la rechaza porque el precio se
  movió, el bot la vigila el resto del minuto y entra a mercado si el precio la cruza, como la llenaría el backtest.
- **Errores de MT5:** si MT5 no entrega posiciones u órdenes, el ciclo falla y reintenta. Antes creía que no tenía
  nada y podía duplicar órdenes.
- **Otros:**
  - un llenado parcial cuenta como entrada;
  - se guarda el ticket de cada orden con su nivel en `estado.json`, de respaldo si el bróker borra el comentario;
  - la hora de la vela nueva manda sobre la del tick (noticias, corte);
  - se verifica la cuenta (`login` del config);
  - un solo bot por magic (candado);
  - el dry-run guarda su estado aparte (`<login>_dryrun`).
- **Arranque:** el bot escribe en el log las reglas del bróker para WS30 (stops level, freeze level, IOC,
  vencimiento) y una prueba `order_check` de una orden lejana (no se envía).

Pruebas después del arreglo:
- simulacros `--todas` 2025-2026 iguales que antes;
- papel y `papel/prueba_offline.py` OK;
- órdenes a MT5 revisadas con un MT5 simulado: 35/35;
- vigilancia, noticias y spread con pruebas dirigidas.
