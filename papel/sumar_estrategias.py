# -*- coding: utf-8 -*-
"""
Suma a papel/config.json (el del VPS, no versionado) las estrategias de papel/config.example.json que todavia no
estan, sin tocar las que ya existen ni los feeds. Antes guarda una copia config.json.bak-<fecha>.

    python papel/sumar_estrategias.py            # muestra que agregaria y lo agrega
    python papel/sumar_estrategias.py --ver      # solo muestra, no cambia nada
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def main():
    real, ejemplo = AQUI / "config.json", AQUI / "config.example.json"
    if not real.exists():
        print("No existe papel/config.json: copia config.example.json a config.json y revisa los feeds.")
        return
    cfg = json.loads(real.read_text(encoding="utf-8"))
    ej = json.loads(ejemplo.read_text(encoding="utf-8"))
    ids = {e["id"] for e in cfg["estrategias"]}
    cuentas = {e["cuenta"] for e in cfg["estrategias"]}
    nuevas = [e for e in ej["estrategias"] if e["id"] not in ids]
    if not nuevas:
        print("config.json ya tiene todas las estrategias del ejemplo:", ", ".join(sorted(ids)))
        return
    for e in nuevas:
        if e["cuenta"] in cuentas:
            print(f"OJO {e['id']}: la cuenta virtual {e['cuenta']} ya la usa otra estrategia. No se agrega nada.")
            return
        if e["feed"] not in cfg["feeds"]:
            print(f"OJO {e['id']}: el feed '{e['feed']}' no esta en config.json. No se agrega nada.")
            return
    print("Se agregan:", ", ".join(f"{e['id']} (feed {e['feed']}, cuenta {e['cuenta']})" for e in nuevas))
    if "--ver" in sys.argv:
        return
    copia = real.with_name(f"config.json.bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(real, copia)
    cfg["estrategias"] += nuevas
    real.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Listo. Copia del anterior en {copia.name}")


if __name__ == "__main__":
    main()
