# Plan de fondeo y distribución de estrategias

> Decidido por el usuario el 10-nov-2026. Leer antes de responder cualquier cosa sobre cuentas, prop firms,
> Darwinex, riesgo por cuenta o qué estrategia va dónde. Si el usuario cambia algo, actualizar este archivo.
> Retiros: `POLITICA_RETIROS.md` (cuánto retirar) y `RETIROS.md` (registro contable).

## Qué estrategia va dónde

| Dónde | Estrategias | Riesgo | Tamaño | Para qué |
|---|---|---|---|---|
| **FTMO, challenges** | OB | F1 1 % · F2 0.5 % | 2 challenges al mes (50k, o 100k con descuento) | Pasar rápido |
| **FTMO, fondeadas** | **Solo OB** | 0.5 % fijo | Hasta el tope de FTMO: $400k antes del scaling (el usuario dijo 450k; el tope oficial es 400k) | Ingreso rotativo: si se quema, es costo del negocio y se repone con un challenge |
| **The5ers, challenges** (High Stakes) | OB | 0.75 % (diaria 4 %, máxima 8 %) | 1 challenge de 50k o 100k a la vez ($249 el de 50k) | Pasar rápido |
| **The5ers, fondeadas** (Pro Trader) | **Pivotes juntos en la misma cuenta**: S/R Pivot H1 + falsa ruptura H1 | **0.4 % cada una** (con máxima 8 %, a 0.5 % se queman demasiado) | Hasta 4 cuentas Pro; cada una escala +10 % hasta $500k | Ingreso estable de largo plazo |
| **Darwinex (DARWIN YGZY)** | OB como hoy + pivotes en real desde el **13-nov-2026** (operan desde el lunes 16-nov) | OB igual que hoy (~$500 por trade) · pivotes **$500 fijos cada una** (0.5 % de los 100k), igual que el OB | Una sola cuenta consolidada (no se abre un 2.º DARWIN: cuesta $50/mes) | Fondo de inversión de largo plazo |

## Cómo entra una estrategia nueva al fondo Darwinex (procedimiento fijo)
1. Investigación con backtest fiel. Se decide con 2026 + 2025; 2020-2024 queda como referencia fuera de muestra.
2. **Papel 2 meses** en el laboratorio (`papel/`, panel Lab · Papel). Condición: papel y backtest coinciden en al
   menos 90 % de los trades, con R parecido y sin errores de ejecución.
3. Real en Darwinex a **0.25 %** el primer mes.
4. Si todo sigue bien, sube a **0.5 %** y queda así.

Pivotes: papel desde el 10-nov-2026. **El 13-nov-2026 el usuario decidió pasarlos a real ya, a 0.5 % ($500 fijos) cada
uno**, sin esperar los 2 meses ni el escalón de 0.25 %. Razones:
- 2 meses de papel no dicen si la estrategia gana.
- La ejecución ya estaba probada: papel = backtest 4/4, simulacros de años completos.
- Lo que falta probar (lote real, llenados, swap) solo se ve en real.

El papel sigue corriendo en paralelo para comparar real, papel y backtest. Al primer trade de cada una, revisar el
lote y los dólares arriesgados. El procedimiento de arriba sigue valiendo para estrategias nuevas, salvo que el
usuario decida otra cosa.

Qué esperar de los 2 meses de papel (las dos juntas): ~45 trades (37 a 50); la S/R hace ~16 al mes y la falsa
ruptura ~6-7. La ganancia de 2 meses no dice si la estrategia sirve. Fuera de muestra (2020-24), 37 % de las
ventanas de 2 meses terminan negativas; la mediana es +2.8R y el 10 % peor está bajo −8.7R. Por eso se decide por
**fidelidad** (mismos trades y R que el backtest del mismo período), no por cuánto ganó.

## Lo que se espera de verdad (no lo de 2026)
- **Pivotes juntas a 0.5 % cada una: ~+8 %/año** (fuera de muestra 2020-24). Puede haber años negativos, como 2020
  (−10 %, caída de 17 %).
  - 2025: +16 %. 2026: +44 %, inflado porque la configuración se eligió con 2026.
- Peor día ~−2 % (con flotante). Peor racha en 2025-26: 8 trades seguidos (−3.3 %); en 2020: 18 (−8.6 %).
- **OB:** 2026 excelente, en backtest y en real. Con el modelo completo, 2023-24 perdió fuerte. Los pivotes ganaron
  justo en esos años (+13.5 % y +17.3 %): esa es la razón de diversificar.

## Riesgos de reglas que el usuario aceptó o hay que vigilar
- **Posiciones opuestas entre cuentas.** FTMO y The5ers lo prohíben "con fines de manipulación", incluso entre
  firmas distintas. OB y pivotes quedan opuestos ~17 veces al mes.
  - Entre FTMO y The5ers: el usuario **asume ese riesgo** (decisión del 10-nov-2026).
  - **Dentro de The5ers es más delicado:** ve sus propias cuentas. Un challenge OB corriendo al mismo tiempo que
    fondeadas de pivotes en The5ers es la combinación más visible. Opciones: pasar los challenges de The5ers con
    los pivotes, o no tener un challenge OB en The5ers mientras haya fondeadas de pivotes ahí.
- **Noticias.** The5ers: "no se permiten movimientos 2 min antes o después de noticias de alto impacto". FTMO
  fondeada normal: cualquier ejecución en ±2 min, incluidos SL, TP y pendientes. El filtro actual de las bots solo
  cubre las 08:30 ET.
- **The5ers "bulk trading":** prohíbe herramientas automáticas que abren varios trades a la vez. Los pivotes pueden
  tener 2 posiciones abiertas. Confirmar con soporte.

## Simulación de pivotes en The5ers (10-nov-2026, `research/pa_lab/estructura_pa/cartera_the5ers.py`)

Las dos variantes de High Stakes ("New" y "Classic") usan hoy diaria 4 % y máxima 8 % (captura del usuario del
10-nov-2026: New 50k = máxima $4.000, objetivos 10/5, retiro mínimo $300, tope $3.000 por ciclo). La columna 5/10
quedó como referencia: era lo que decía la página.

| Fondeada, 12 meses | **4 % / 8 % (lo que hay)** | 5 % / 10 % (referencia) |
|---|---|---|
| 0.5 % c/u, 2025-26 | nunca pierde · +30 %/año | nunca pierde · +30 %/año |
| 0.5 % c/u, 2020-24 (fuera de muestra) | **pierde 26 %** de las veces · +12 %/año | pierde 15 % · +11 %/año |
| 0.4 % c/u, 2020-24 | pierde 15 % · +9 %/año | **pierde 4 %** · +8 %/año |

Challenge con pivotes, F1 0.75 % / F2 0.5 % c/u:
- Classic: pasa 88 % (2025-26) y 54 % (2020-24), en ~3 meses.
- New: pasa 96 % y 66 %, en ~4 meses.

## Pendientes de decidir o confirmar
- [x] Riesgo de los pivotes en las fondeadas de The5ers: **0.4 % cada una** (con máxima 8 %: fuera de muestra se
      quema 15 % de las veces contra 26 % a 0.5 %).
- [ ] Tope de pago por ciclo en The5ers: $3.000 en 50k y $4.000 en 100k. Con los pivotes (~8 %/año) no limita.
- [ ] Preguntar a The5ers por escrito:
  - posiciones opuestas con otra firma;
  - "bulk trading" con 2 posiciones;
  - si la pérdida diaria se mide sobre balance o equity, y a qué hora se reinicia;
  - si una pendiente que se llena dentro de ±2 min de una noticia es infracción;
  - el tope total de capital.
- [x] Arreglos de los bots en papel (auditoría del 10-nov-2026): arranque con posición del backtest, feriados,
      reinicios del VPS, minuto del cierre, desempate. Commit 7582152, corriendo en el VPS desde el 10-nov 20:49.
- [x] Modo real de la falsa ruptura (órdenes STOP en MT5, magic 345691, vencimiento 8 h), 13-nov-2026.
      Simulacro: 76/76 (2025) y 66/67 (2026; la diferencia es Juneteenth sin feriados).
- [x] Modo real, apertura con gap (01:00 servidor o lunes). Si el gap cruza dos pendientes, MT5 llena las dos; el
      backtest, una.
  - Desde el 13-nov-2026 los dos bots se quedan con la del backtest (la más cercana a la apertura) y cierran las
    demás al minuto siguiente.
  - Esos niveles u órdenes quedan sin usar.
  - Simulacro `--todas`, 2025-26: de 1 a 4 casos por año, costo −0.1R a +0.06R.

Fuentes: [The5ers High Stakes](https://the5ers.com/high-stakes/) ·
[The5ers prácticas prohibidas](https://the5ers.com/faqs/prohibited-trading-practices/) ·
[FTMO prácticas prohibidas](https://ftmo.com/en/forbidden-trading-practices/) ·
[FTMO noticias](https://ftmo.com/en/faq/can-i-trade-news/)
