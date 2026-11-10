# -*- coding: utf-8 -*-
"""
Calendario del corte de fin de semana de los bots del laboratorio (Dow, CFD sobre el futuro). Hora SERVIDOR = Nueva
York + 7 h (FTMO y Darwinex).

Corte normal: viernes 19:00 UTC (22:00 servidor con horario de verano de EE.UU., 21:00 sin): se cierra la posicion,
se cancelan las pendientes y no se abre nada hasta el lunes. Es la regla del bot OB en vivo.

Problema que resuelve (auditoria 10-nov-2026): en semanas cortas por feriado el mercado cierra ANTES de esa hora (o el
viernes ni abre) y el corte nunca se disparaba: la posicion y las pendientes quedaban todo el fin de semana largo.
Ahora la semana termina en su ULTIMO dia con mercado, y el corte es:
  - dia normal: 19:00 UTC, como siempre;
  - dia con cierre temprano: 15 min antes de ese cierre.

CIERRES = dias de semana con cierre temprano ("HH:MM" hora de Nueva York) o cerrados (None). Solo importan los que
caen al final de la semana (un feriado a mitad de semana no cambia el corte). Historico 2020-2026 sacado de las velas
M1 de FTMO (ultima vela de cada semana corta); 2026-11 en adelante segun el calendario de NYSE/CME, a confirmar con el
horario que publica el broker un mes antes.
"""
import pandas as pd

SERVIDOR_MENOS_ET = pd.Timedelta(hours=7)
MARGEN = pd.Timedelta(minutes=15)

CIERRES = {
    # historico (velas FTMO)
    "2020-04-10": None, "2020-07-03": "13:00", "2020-11-27": "13:15", "2020-12-24": "13:15", "2020-12-25": None,
    "2021-01-01": None, "2021-04-02": "09:15", "2021-11-26": "13:15", "2021-12-24": None, "2022-04-15": None,
    "2022-11-25": "13:15", "2023-04-07": "09:15", "2023-11-24": "12:15", "2024-03-29": None, "2024-11-29": "13:15",
    "2025-04-18": None, "2025-07-04": "13:00", "2025-11-28": "13:15", "2026-04-03": "09:15", "2026-06-19": "13:00",
    "2026-07-03": "13:00",
    # proximos
    "2026-11-27": "13:15",                          # viernes despues de Accion de Gracias
    "2026-12-24": "13:15", "2026-12-25": None,      # Navidad: jueves corto, viernes cerrado
    "2027-01-01": None,                             # Ano Nuevo: la semana termina el jueves 31-12 (dia normal)
    "2027-03-26": None,                             # Viernes Santo
    "2027-06-18": "13:00",                          # Juneteenth (19-jun cae sabado: se observa el viernes)
    "2027-11-26": "13:15",
    "2027-12-24": None,                             # Navidad (25-dic cae sabado: se observa el viernes)
}
_CIERRES = {pd.Timestamp(k): v for k, v in CIERRES.items()}


def verano_eeuu(t: pd.Timestamp) -> bool:
    mar1 = pd.Timestamp(t.year, 3, 1)
    nov1 = pd.Timestamp(t.year, 11, 1)
    ini = mar1 + pd.Timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    fin = nov1 + pd.Timedelta(days=(6 - nov1.weekday()) % 7)
    return ini <= t.normalize() < fin


def _corte_del_dia(dia: pd.Timestamp) -> pd.Timestamp:
    """Hora servidor del corte si la semana termina ese dia."""
    c = _CIERRES.get(dia)
    if isinstance(c, str):
        return dia + pd.Timedelta(hours=int(c[:2]), minutes=int(c[3:5])) + SERVIDOR_MENOS_ET - MARGEN
    return dia + pd.Timedelta(hours=22 if verano_eeuu(dia) else 21)


def corte_de_la_semana(t: pd.Timestamp) -> pd.Timestamp:
    """Momento (hora servidor) del corte de la semana de `t` (lunes a domingo)."""
    t = pd.Timestamp(t)
    dia = t.normalize() + pd.Timedelta(days=4 - t.weekday())          # el viernes de esa semana
    while dia in _CIERRES and _CIERRES[dia] is None and dia.weekday() > 0:
        dia -= pd.Timedelta(days=1)                                   # viernes cerrado -> la semana termina antes
    return _corte_del_dia(dia)


def corte_semana(t: pd.Timestamp, feriados: bool = True) -> bool:
    """True desde el corte de la semana hasta el domingo. feriados=False = la regla vieja (solo el viernes a las
    19:00 UTC), que es la de los motores de investigacion: la usan las pruebas de paridad."""
    t = pd.Timestamp(t)
    if not feriados:
        return t.weekday() == 4 and t.hour >= (22 if verano_eeuu(t) else 21)
    lunes_sig = t.normalize() + pd.Timedelta(days=7 - t.weekday())
    return corte_de_la_semana(t) <= t < lunes_sig


def ultimo_corte(t: pd.Timestamp, feriados: bool = True) -> pd.Timestamp:
    """El corte de fin de semana mas reciente que ya paso (<= t): el de esta semana o el de la anterior."""
    def corte(x):
        if feriados:
            return corte_de_la_semana(x)
        viernes = x.normalize() + pd.Timedelta(days=4 - x.weekday())
        return viernes + pd.Timedelta(hours=22 if verano_eeuu(viernes) else 21)
    t = pd.Timestamp(t)
    c = corte(t)
    return c if c <= t else corte(t - pd.Timedelta(days=7))
