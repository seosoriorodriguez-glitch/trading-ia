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

## Agregar una estrategia
1. **Si es otra configuración de una que ya existe**, por ejemplo el S/R con otros parámetros u otro símbolo: una
   entrada nueva en `config.json` con:
   - `id` que empiece con `lab_`.
   - `cuenta` única ≥ 9000000000.
   - `feed`: la terminal de la que lee precios.
   - `destino`: `darwinex` o `ftmo`.
2. **Si es una estrategia nueva:** su lógica y su bot (como `strategies/sr_pivot_live/`), una línea en
   `estrategias.py` (`PLUGINS` y `BACKTESTS`) y la referencia de su backtest en `panel/web/lib/lab.ts` (`LAB`),
   para que el panel la compare contra lo esperado.

## Pruebas (sin conexión, no tocan nada)
- `python papel/prueba_offline.py 2026-09-01 2026-10-01`: el laboratorio completo con un MT5 falso (ticks armados
  con velas M1) y un Supabase falso. Revisa las filas que se subirían y la comparación con el backtest
  (sep-2026: 16/16).
- `python strategies/sr_pivot_live/herramientas/paridad.py`: la lógica del S/R contra el backtest de investigación.
  Da 163/163 trades idénticos en 2026 y 192/192 en 2025.

## Qué mirar en el panel
Un mes en papel sirve para comprobar que la estrategia **se ejecuta como en el backtest**: mecánica, costos, swap y
horarios. **No sirve para saber si gana**, porque con pocas decenas de trades el resultado es ruido. Lo importante
es el cuadro **"Papel vs backtest del mismo período"**. Si los trades coinciden, la estrategia está lista para
pasar al destino. Si dejan de coincidir, algo se ejecuta distinto.
