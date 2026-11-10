# Falsa ruptura de pivotes H1 (laboratorio en papel)

Solo corre **en papel** dentro de `papel/runner.py`: usa los precios en vivo de la terminal y sus órdenes son virtuales.
No envía nada al broker. Tiene carpeta propia y no toca los bots en producción ni el bot S/R. Del S/R solo
**hereda** el broker de papel y los horarios, sin modificarlos.

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
- **Riesgo:** 0.5 % de 100 000 virtuales.
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
