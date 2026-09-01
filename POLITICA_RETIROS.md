# Politica de retiros — cuentas de fondeo

> Regla decidida el 2026-08-29. Aplica a las cuentas FTMO y Darwinex.
> El proposito es que la decision de retirar este tomada **antes** de estar
> frente al boton, no en el momento.

---

## 1. La regla

**Cuando la ganancia sobre el ultimo piso llegue a +$1.000 (10% de una cuenta
de 10k), retirar la MITAD y subir el piso.**

No "retirar hasta dejar un colchon fijo". La diferencia es todo.

| Ciclo | Llega a | Retira (bruto) | Queda | Colchon | Al bolsillo (80%) |
|---|---|---|---|---|---|
| 1 | $11.000 | $500 | $10.500 | 5%  | $400 |
| 2 | $11.500 | $500 | $11.000 | 10% | $400 |
| 3 | $12.000 | $500 | $11.500 | 15% | $400 |
| 4 | $12.500 | $500 | $12.000 | 20% | $400 |

Cobras en cada ciclo igual, pero el colchon crece en vez de quedarse fijo.

---

## 2. Por que un colchon fijo no sirve

FTMO mide la perdida maxima **desde el balance inicial**, no desde el pico.
El piso esta clavado en $9.000 y no se mueve. Eso juega a favor: mientras la
cuenta crece, el margen porcentual crece con ella.

| Balance | Colchon | Margen hasta $9.000 | % del balance |
|---|---|---|---|
| $10.000 | 0%  | $1.000 | **10,0%** |
| $10.500 | 5%  | $1.500 | **14,3%** |
| $11.000 | 10% | $2.000 | **18,2%** |
| $11.500 | 15% | $2.500 | **21,7%** |
| $12.000 | 20% | $3.000 | **25,0%** |

Drawdowns documentados del motor (ver `BACKTEST_SPEC.md` seccion 4):
**14,9%** (2024) · **20,1%** (2025) · **14,8%** (2026 a agosto).

Cruzando ambas tablas:

- Colchon 5%  -> 14,3% de margen: **revienta en 2024 y en 2025**
- Colchon 10% -> 18,2% de margen: aguanta 2024, **revienta en 2025**
- Colchon 15% -> 21,7% de margen: **aguanta los tres anios**

Un colchon fijo del 4-5% no habria sobrevivido ninguno de los tres anios
medidos. No es escenario de cola: es el anio promedio.

---

## 3. El error de razonamiento que esto corrige

Que el drawdown llegue justo despues de un retiro **no es mala suerte**.

Retirar es, por construccion, el acto que te deja en el minimo colchon
posible. El momento inmediatamente posterior a un retiro es el de maxima
fragilidad de todo el ciclo. Entonces "morir justo despues de retirar" no es
la casualidad desafortunada: es **la forma mas probable de morir**.

Un colchon fijo repetido ciclo tras ciclo mantiene constante la probabilidad
de ruina. Una probabilidad constante repetida muchas veces converge a 1.
No es si pasa, es cuando.

---

## 4. Datos live que respaldan esto

Periodo con la config actual (sesion London 10:00-17:00), 01-jun a 06-ago 2026:

| Metrica | Live real | Backtest (motor STOP) |
|---|---|---|
| Trades | 130 | — |
| Trades/dia | 2,71 | 2,68 esperado |
| WR | 40,0% | 40,9% |
| PF | **1,615** | 1,51 |
| R/trade | +0,557 | — |
| Max DD | **7,58%** | 12-20% anual |

El motor reproduce el live. **Pero el DD de 7,58% es sobre 48 dias**, no
sobre un anio. Una ventana de dos meses siempre va a mostrar un DD menor que
la serie completa. No usar ese 7,58% para justificar un colchon chico.

---

## 5. Antes de apretar el boton de retiro

- [ ] Verificar si FTMO permite **retiro parcial**. El dialogo de "Reclamar
      Recompensa" cierra la cuenta y emite una nueva de $10.000: en ese flujo
      no existe dejar colchon.
- [ ] Recordar que el split es **80:20**. Sobre $600 de ganancia se reciben
      ~$480, no $600. Planificar con el neto.
- [ ] Chequear el **plan de escalado** de FTMO. Si sigue vigente, dejar crecer
      la cuenta vale mas que los $100 extra por ciclo.
- [ ] Anotar el retiro en CLP con el **dolar observado del dia** (ver
      obligaciones tributarias — renta mundial, Formulario 22 en abril).

---

## 6. Que limite es el que mata

El **10% de perdida total**, no el 5% diario.

Con 0,5% por trade y maximo 2 simultaneas se arriesga 1% a la vez; llegar al
5% en un dia requiere cinco perdidas completas seguidas. Posible pero raro.
El que alcanza es el acumulado.
