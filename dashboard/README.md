# Dashboard interno de backtests — Order Block

Uso **personal/local**. Visualiza backtests del motor real M5+M1 con gráficos (velas + zonas OB +
trades), métricas, curva de equity, e historial de runs. **100% aditivo**: solo importa el motor
en modo lectura, no modifica ninguna estrategia de producción.

## Instalar y correr

```bash
# desde la raíz del proyecto, con el venv activo
pip install -r dashboard/requirements.txt      # instala streamlit (plotly ya está)
streamlit run dashboard/app.py
```

Abre `http://localhost:8501`.

## Qué hace

- **Backtest (botones):** elige activo (de `data/`), sesión (london/ny/both/24_7), RR, costo y
  riesgo → corre el motor real y muestra métricas + equity + gráfico de velas con zonas OB y trades.
  Puedes **enfocar un trade** para hacer zoom a su zona (ideal para depurar).
- **Guardar:** cada run (config + métricas + tus notas) se guarda en `runs.db` (SQLite local) y sus
  trades en `runs/<id>.csv`.
- **Historial:** lista de runs, recargar cualquiera (gráfico instantáneo), y **comparar A vs B**
  (métricas + curvas de equity superpuestas).

## Puente conversación → UI

Cuando corremos backtests hablando, se pueden guardar en el mismo `runs.db` con notas de análisis,
y aparecen aquí en **Historial**. Es la misma máquina/motor, sin duplicar lógica.

## Arquitectura (archivos)

| Archivo | Rol |
|---|---|
| `backtest_runner.py` | Wrapper llamable del motor (replica ASSETS/SESSIONS/escalado de `ob_multiasset.py`) |
| `charts.py` | Figuras Plotly (velas+zonas+trades, equity, overlay comparación) |
| `storage.py` | Persistencia SQLite local + CSV de trades por run |
| `app.py` | La app Streamlit |

No versionar `runs.db` ni `runs/` (ver `.gitignore`).
