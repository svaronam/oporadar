"""BOE · Sección II.B (Oposiciones y concursos) vía la API de datos abiertos.

Aquí sale TODO lo estatal y, además, el extracto de las convocatorias de ayuntamientos, diputaciones,
universidades y comunidades autónomas (para las entidades locales, el plazo de solicitudes empieza a contar
justo desde ese extracto en el BOE).
"""
import json
import urllib.error
import xml.etree.ElementTree as ET

from ..util import fetch

API = "https://www.boe.es/datosabiertos/api/boe/sumario/{fecha}"


def _url(x):
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get("texto") or x.get("#text") or x.get("url")
    return None


def _lista(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _recorrer(nodo, ctx, out):
    if isinstance(nodo, list):
        for n in nodo:
            _recorrer(n, ctx, out)
        return
    if not isinstance(nodo, dict):
        return
    if "identificador" in nodo and "titulo" in nodo:
        out.append((nodo, ctx))
        return
    for k, v in nodo.items():
        if k in ("data", "sumario", "diario", "seccion", "departamento", "epigrafe", "item"):
            for hijo in _lista(v):
                c2 = dict(ctx)
                if isinstance(hijo, dict) and k in ("seccion", "departamento", "epigrafe"):
                    c2[k] = {"codigo": hijo.get("codigo"), "nombre": hijo.get("nombre")}
                _recorrer(hijo, c2, out)


def candidatos(fecha):
    """fecha: datetime.date. Devuelve lista de candidatos de la sección II.B ([] si ese día no hay BOE)."""
    try:
        txt, _ = fetch(API.format(fecha=fecha.strftime("%Y%m%d")), accept="application/json")
    except urllib.error.HTTPError as e:
        if e.code == 404:  # domingo o día sin boletín
            return []
        raise
    data = json.loads(txt)
    items = []
    _recorrer(data, {}, items)
    out = []
    for it, ctx in items:
        sec = ctx.get("seccion") or {}
        if not (str(sec.get("codigo", "")).upper() == "2B" or "oposiciones y concursos" in str(sec.get("nombre", "")).lower()):
            continue
        ident = it.get("identificador")
        url_xml = _url(it.get("url_xml")) or f"https://www.boe.es/diario_boe/xml.php?id={ident}"
        out.append({
            "uid": f"BOE:{ident}",
            "fuente": "BOE",
            "fecha_pub": fecha,
            "titulo": it.get("titulo", "").strip(),
            "departamento": (ctx.get("departamento") or {}).get("nombre", "") or "",
            "epigrafe": (ctx.get("epigrafe") or {}).get("nombre", "") or "",
            "url": _url(it.get("url_html")) or f"https://www.boe.es/diario_boe/txt.php?id={ident}",
            "url_pdf": _url(it.get("url_pdf")),
            "get_texto": (lambda u=url_xml: texto_xml(u)),
            "fuente_zona": None,
        })
    return out


def texto_xml(url):
    txt, _ = fetch(url, accept="application/xml")
    try:
        root = ET.fromstring(txt.encode("utf-8"))
    except ET.ParseError:
        return ""
    nodo = root.find(".//texto")
    if nodo is None:
        return ""
    partes = [t.strip() for t in nodo.itertext() if t.strip()]
    return "\n".join(partes)
