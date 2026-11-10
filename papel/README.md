# Laboratorio en papel

Paper trading de estrategias nuevas con los **precios en vivo** del bróker, antes de comprar un challenge o pasarlas a
real. Los resultados aparecen en el panel, en **Lab · Papel**.

## Regla de oro: 100 % aditivo
- **No envía ninguna orden.** Solo lee precios de una terminal MT5 que ya existe, igual que el colector del panel.
  Órdenes, posiciones y balance son virtuales.
- **No importa ni modifica ningún bot en producción.** Puede leer la misma terminal que el bot OB sin interferir:
  cada proceso se conecta por su cuenta.
- **En Supabase solo escribe filas `lab_…`** en `bots`, `trades`, `account_snapshots` y `trade_candles`:
  - Usa cuentas virtuales ≥ 9 000 000 000 y tickets = cuenta × 100 000 + n, que nunca chocan con los reales.
  - No crea tablas ni cambia columnas.
  - El panel saca los `lab_` del portafolio real, de las alertas y de la "última recolección".
- **Para quitar una estrategia:** `"activa": false` en el config y relanzar. En el panel, `active = false` en `bots`
  la oculta sin borrar nada.

## Cómo funciona
- `runner.py` corre las estrategias del config que usan un mismo **feed** (una terminal). Hay un proceso por feed,
  porque la librería de MT5 solo se conecta a una terminal por proceso.
- Cada estrategia tiene una cuenta virtual propia (100k al 0.5% por defecto) y su bot en modo papel:
  - Llena las órdenes con **cada tick real** (bid/ask), no con una mirada cada 2 segundos.
  - Descuenta el **swap real** del símbolo en cada medianoche del servidor, incluido el día triple.
  - Cierra el viernes como el bot real.
- Cada 60 s sube los trades cerrados (con las velas M5 para el gráfico). Cada 5 min sube un snapshot, que hace de
  latido en el panel: "en línea" o "sin latido hace X".
- Una vez al día, pasada la 01:00 del servidor, corre **el backtest de la estrategia sobre las velas del mismo
  bróker y del mismo período** y lo compara trade por trade con el papel (`fidelidad.py`). El backtest se guarda
  como `<id>__bt`, archivado, y se ve en el detalle de la estrategia.
- Si se apaga, al relanzar sigue donde iba (`papel/estado/<id>/`) y procesa los ticks del tiempo que estuvo
  apagado. En la realidad las órdenes habrían quedado puestas en el servidor.

## En el VPS
```powershell
git pull
copy papel\config.example.json papel\config.json      # una vez; revisar rutas de terminales
$env:SUPABASE_URL="https://....supabase.co"            # las mismas variables que el colector
$env:SUPABASE_SERVICE_KEY="<service_role_key>"
python papel/runner.py --feed darwinex                 # en su propia ventana, como el colector
```
- **Detener:** crear `papel\STOP_PAPEL.txt` (o Ctrl+C). Borrar el archivo antes de relanzar.
- **Probar sin subir nada:** agregar `--sin-panel`.
- **Logs:**
  - `papel/estado/runner_<feed>.log`.
  - `papel/estado/<id>/eventos.log`: cada orden, llenado, swap y cierre.
  - `papel/estado/<id>/trades.csv` y `papel/estado/<id>/fidelidad.json`.

## Arreglos de la auditoría del 10-nov-2026
Una auditoría independiente buscó en qué situaciones el bot en papel (y en real) se separaría del backtest.
Arreglado en los dos bots:
- **Arranque con el backtest en posición.** El calentamiento detecta la posición que el backtest tendría abierta.
  Marca su nivel como usado y el bot queda ocupado ("posición sombra") hasta que esa posición habría cerrado.
  Antes, la S/R repetía ese nivel en 12 de 12 casos probados.
- **Minuto del cierre.** No se decide nada en el minuto en que cerró una posición ni en el minuto del arranque,
  porque el backtest espera la vela siguiente.
- **Feriados** (`papel/calendario.py`). La semana termina en su último día con mercado: el corte es a las 19:00 UTC,
  o 15 min antes de un cierre temprano. Próximos: viernes 27-nov, jueves 24-dic y jueves 31-dic.
- **Caídas del VPS.** El broker de papel aplica corte, noticias y vencimientos aunque el bot no corra. Al llenarse
  una orden cancela las demás. Si al volver el bot encuentra una posición abierta antes de un corte, la cierra.
- **Desempate.** Si un salto cruza dos órdenes, se llena la que el precio tocó primero.
- **Comparación diaria más limpia:**
  - con el spread de cada vela y los precios redondeados al tick, como el bot;
  - empareja por nivel;
  - calcula el R con el riesgo nominal;
  - corre en la pausa diaria del mercado (00:05-00:55 del servidor), así no le quita tiempo a los bots.
- **Candado:** no pueden correr dos laboratorios con el mismo feed a la vez.
- Una orden que no se puede poner queda en el log.

## Estrategias en papel
| id | Qué es | Carpeta |
|---|---|---|
| `lab_sr_pivot_h1` | S/R Pivot al toque H1 (LIMIT) | `papel/estrategias/sr_pivot_h1/` |
| `lab_falsa_ruptura_h1` | Falsa ruptura de pivotes H1 (STOP en contra de la ruptura) | `papel/estrategias/falsa_ruptura_h1/` |

## Agregar una estrategia
Para sumar al `config.json` del VPS las estrategias nuevas del ejemplo, sin tocar las que ya están:
`python papel/sumar_estrategias.py`. Guarda antes una copia `config.json.bak-<fecha>`.

1. **Si es otra configuración de una que ya existe**, por ejemplo el S/R con otros parámetros u otro símbolo: una
   entrada nueva en `config.json` con:
   - `id` que empiece con `lab_`.
   - `cuenta` única ≥ 9000000000.
   - `feed`: la terminal de la que lee precios.
   - `destino`: `darwinex` o `ftmo`.
2. **Si es una estrategia nueva:** su lógica y su bot (como `papel/estrategias/sr_pivot_h1/`), una línea en
   `registro.py` (`PLUGINS` y `BACKTESTS`) y la referencia de su backtest en `panel/web/lib/lab.ts` (`LAB`),
   para que el panel la compare contra lo esperado.

## Pruebas (sin conexión, no tocan nada)
- `python papel/prueba_offline.py 2026-09-01 2026-10-01`: el laboratorio completo con un MT5 falso (ticks armados
  con velas M1) y un Supabase falso. Revisa las filas que se subirían y la comparación con el backtest
  (sep-2026: S/R 16/16, falsa ruptura 7/7).
- `python papel/estrategias/sr_pivot_h1/herramientas/paridad.py`: la lógica del S/R contra el backtest de investigación.
  Da 163/163 trades idénticos en 2026 y 192/192 en 2025.
- `python papel/estrategias/falsa_ruptura_h1/herramientas/paridad.py`: lo mismo para la falsa ruptura. Da 67/67 en
  2026 y 76/76 en 2025.
- `python papel/estrategias/falsa_ruptura_h1/herramientas/prueba_papel.py 2026-09-01 2026-10-01`: el bot de la falsa
  ruptura en papel con ticks falsos, incluido el calentamiento.

## Qué mirar en el panel
Un mes en papel sirve para comprobar que la estrategia **se ejecuta como en el backtest**: mecánica, costos, swap y
horarios. **No sirve para saber si gana**, porque con pocas decenas de trades el resultado es ruido. Lo importante
es el cuadro **"Papel vs backtest del mismo período"**. Si los trades coinciden, la estrategia está lista para
pasar al destino. Si dejan de coincidir, algo se ejecuta distinto.
