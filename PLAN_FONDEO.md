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
| **Darwinex (DARWIN YGZY)** | OB como hoy + pivotes desde el **10-ene-2027** | OB igual que hoy · pivotes 0.25 % cada una el 1er mes, luego **0.5 % cada una para siempre** | Una sola cuenta consolidada (no se abre un 2.º DARWIN: cuesta $50/mes) | Fondo de inversión de largo plazo |

## Cómo entra una estrategia nueva al fondo Darwinex (procedimiento fijo)
1. Investigación con backtest fiel. Se decide con 2026 + 2025; 2020-2024 queda como referencia fuera de muestra.
2. **Papel 2 meses** en el laboratorio (`papel/`, panel Lab · Papel). Condición: papel y backtest coinciden en al
   menos 90 % de los trades, con R parecido y sin errores de ejecución.
3. Real en Darwinex a **0.25 %** el primer mes.
4. Si todo sigue bien, sube a **0.5 %** y queda así.

Pivotes: papel desde el 10-nov-2026 → real el 10-ene-2027 si pasan la validación.

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
- [ ] Arreglos de los bots en papel antes del real (auditoría del 10-nov-2026): arranque con posición del backtest,
      feriados (27-nov, 24-25 dic, 31 dic-1 ene), reinicios del VPS, minuto del cierre, desempate S/R.
- [ ] La falsa ruptura todavía no tiene modo real (órdenes STOP en MT5): hay que hacerlo antes del 10-ene.

Fuentes: [The5ers High Stakes](https://the5ers.com/high-stakes/) ·
[The5ers prácticas prohibidas](https://the5ers.com/faqs/prohibited-trading-practices/) ·
[FTMO prácticas prohibidas](https://ftmo.com/en/forbidden-trading-practices/) ·
[FTMO noticias](https://ftmo.com/en/faq/can-i-trade-news/)
