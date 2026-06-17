#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
actualizar_peru_bcrp.py
-----------------------
Descarga la produccion minera mensual nacional por mineral desde la API de
BCRPData (Banco Central de Reserva del Peru; fuente original INEI/MINEM) y
genera data_peru.json para el tablero de Inversiones Adriana.

El tablero (dashboard_produccion_minera_peru.html) ya intenta consultar el BCRP
en vivo desde el navegador. Si tu red/navegador bloquea esa API por CORS, corre
este script (lado servidor: sin CORS) y deja data_peru.json junto al HTML; el
tablero lo lee al abrir.

Uso:
    pip install requests
    python actualizar_peru_bcrp.py            # 2008 -> hoy
    python actualizar_peru_bcrp.py 2015       # desde 2015

Salida:
    data_peru.json  (serie NACIONAL mensual por mineral)

Notas:
- Unidades BCRP: cobre/zinc/plomo/estano/hierro/molibdeno en miles de TMF (kt);
  oro y plata en kilogramos -> se convierten a toneladas finas (t) (/1000).
- El detalle POR UNIDAD MINERA no esta en el BCRP; eso viene de los Cuadros
  Estadisticos del MINEM (se cargan aparte en el tablero).
"""

import json
import sys
import datetime as dt

# Codigo BCRP -> (nombre mostrado, unidad destino, divisor desde unidad BCRP)
SERIES = {
    "PN01873AM": ("Cobre",      "kt", 1),       # miles de toneladas
    "PN01876AM": ("Oro",        "t",  1000),    # kilogramos -> t
    "PN01877AM": ("Plata",      "t",  1000),    # kilogramos -> t
    "PN01879AM": ("Zinc",       "kt", 1),
    "PN01878AM": ("Plomo",      "kt", 1),
    "PN01874AM": ("Estaño",     "kt", 1),
    "PN01875AM": ("Hierro",     "kt", 1),
    "PN01880AM": ("Molibdeno",  "kt", 1),
}

MESES = {"ene": 0, "feb": 1, "mar": 2, "abr": 3, "may": 4, "jun": 5,
         "jul": 6, "ago": 7, "set": 8, "sep": 8, "oct": 9, "nov": 10, "dic": 11}


def parse_period(name):
    """'Ene.2025' / 'Set.2025' -> (anio, mes0)."""
    t = str(name).strip().lower().replace(".", " ").replace("-", " ")
    parts = t.split()
    for i, p in enumerate(parts):
        if p[:3] in MESES and i + 1 < len(parts) and parts[i + 1].isdigit():
            return int(parts[i + 1]), MESES[p[:3]]
    # formato YYYY M
    nums = [x for x in parts if x.isdigit()]
    if len(nums) >= 2 and len(nums[0]) == 4:
        return int(nums[0]), int(nums[1]) - 1
    return None


def main():
    import requests

    start = sys.argv[1] if len(sys.argv) > 1 else "2008"
    codes = "-".join(SERIES.keys())
    end_year = dt.date.today().year + 1
    url = (f"https://estadisticas.bcrp.gob.pe/estadisticas/series/api/"
           f"{codes}/json/{start}-1/{end_year}-12/esp")
    print(f"Descargando BCRP: {url}")
    r = requests.get(url, timeout=120, headers={
        "User-Agent": "iA-dashboard/1.0", "Accept": "application/json"})
    r.raise_for_status()
    j = r.json()

    # El orden de j["config"]["series"] sigue el orden de los codigos en la URL
    order = list(SERIES.keys())
    minerals = {SERIES[c][0]: {} for c in order}  # nombre -> {anio(str): [12]}

    for per in j.get("periods", []):
        pp = parse_period(per.get("name", ""))
        if not pp:
            continue
        y, mo = pp
        vals = per.get("values", [])
        for i, code in enumerate(order):
            name, unit, div = SERIES[code]
            raw = vals[i] if i < len(vals) else None
            if raw in (None, "", "n.d.", "n.d"):
                v = None
            else:
                try:
                    v = float(str(raw).replace(",", "")) / div
                except ValueError:
                    v = None
            minerals[name].setdefault(str(y), [None] * 12)[mo] = v

    out = {"minerals": {}, "updated": dt.date.today().isoformat(),
           "source": "BCRPData (INEI/MINEM) - produccion minera mensual nacional"}
    last_label = "?"
    for code in order:
        name, unit, _ = SERIES[code]
        series = minerals[name]
        if not series:
            continue
        out["minerals"][name] = {"unit": unit, "national": series}
        # ultimo mes con dato (para log)
        for y in sorted(series, key=int, reverse=True):
            arr = series[y]
            for mo in range(11, -1, -1):
                if arr[mo] is not None:
                    last_label = f"{name}: {['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][mo]} {y}"
                    break
            else:
                continue
            break

    with open("data_peru.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    yrs = sorted({int(y) for m in out["minerals"].values() for y in m["national"]})
    print(f"data_peru.json escrito · {len(out['minerals'])} minerales · "
          f"{yrs[0]}–{yrs[-1]} · ej. {last_label}")
    print("Deja data_peru.json junto al HTML del tablero (o publicalo en tu GitHub Pages).")


if __name__ == "__main__":
    main()
