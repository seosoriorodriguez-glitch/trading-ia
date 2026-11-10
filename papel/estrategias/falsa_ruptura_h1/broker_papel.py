# -*- coding: utf-8 -*-
"""
MODO PAPEL de la falsa ruptura: el broker de papel del S/R (papel/estrategias/sr_pivot_h1/broker_papel.py), que desde
nov-2026 maneja LIMIT y STOP, el desempate por el precio tocado primero, el vencimiento de cada pendiente (`hasta` de
la orden: 8 h) y las reglas de corte / noticias aunque el bot no corra. Aca solo cambia el prefijo del comentario
('FR <clave>') para saber que niveles ya se operaron. Precios en vivo de la terminal; NO envia nada al broker.
"""
from papel.estrategias.sr_pivot_h1.broker_papel import BrokerPapel

from .estrategia import clave_de_comentario


class BrokerPapelFR(BrokerPapel):
    def claves_usadas(self, dias=None):
        return {clave_de_comentario(h["comentario_entrada"]) for h in self.hist.values()} - {None}
