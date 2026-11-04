"""BOC · Boletín Oficial de Cantabria, apartados 2.2 «Cursos, oposiciones y concursos» y 2.3 «Otros».

Verificado contra la web real (oct. 2026):
- El calendario de la portada se pinta con JavaScript a partir de
  POST /boces/busquedaBoletines.do?mes=M&year=AAAA → JSON [{id, fecBolMilis, tipoBol (0=ordinario), numBol}]
- Sumario ordinario: /boces/verBoletin.do?idBolOrd=ID ; extraordinario: /boces/verBoletinExtraordinario.do?id=ID
- En el sumario: <span class="spanH5">2.2.Cursos, Oposiciones y Concursos</span>,
  organismo <span class="spanH4">, unidad <span class="spanH6">, título <p>, y el PDF
  verAnuncioAction.do?idAnuBlob=N con el texto «PDF (BOC-2026-8321 - 1,31 Mb)».
Las bases completas de ayuntamientos y del Gobierno de Cantabria salen aquí antes que el extracto del BOE.
"""
import datetime as dt
import json
import os
import re
import urllib.parse

from ..util import fetch, fetch_text, norm
from .bloques import SELECTIVO, bloques

BASE = "https://boc.cantabria.es/boces/"
ID_BOC = re.compile(r"BOC-\d{4}-\d+")
_cache_mes = {}


def _debug(nombre, html, data_dir):
    if data_dir:
        d = os.path.join(data_dir, "debug")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, nombre), "w", encoding="utf-8") as f:
            f.write(html)


def boletines_del_mes(anio, mes):
    hoy = dt.date.today()
    clave = (anio, mes)
    if clave not in _cache_mes or (anio, mes) == (hoy.year, hoy.month):
        txt, _ = fetch(f"{BASE}busquedaBoletines.do?mes={mes}&year={anio}", accept="application/json", data=b"")
        _cache_mes[clave] = json.loads(txt)
    return _cache_mes[clave]


def urls_boletin_del_dia(fecha, data_dir=None, plantilla=None):
    """URLs de los boletines (ordinario y extraordinarios) publicados ese día. [] si no hubo."""
    if plantilla:
        return [plantilla.format(dd=f"{fecha.day:02d}", mm=f"{fecha.month:02d}", yyyy=fecha.year)]
    out = []
    for b in boletines_del_mes(fecha.year, fecha.month):
        # fecBolMilis es la medianoche en hora de Madrid; sumamos 12 h para no depender de la zona horaria
        f = (dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=b["fecBolMilis"]) + dt.timedelta(hours=12)).date()
        if f != fecha:
            continue
        if b.get("tipoBol") == 0:
            out.append(f"{BASE}verBoletin.do?idBolOrd={b['id']}")
        else:
            out.append(f"{BASE}verBoletinExtraordinario.do?id={b['id']}")
    return out


SECCIONES = re.compile(r"^2\.\s*[23]\b|oposiciones y concursos")


def anuncios(url_boletin, data_dir=None):
    """[(titulo, url_pdf, organismo, id_boc, seccion)] de los apartados 2.2 y 2.3."""
    html, _ = fetch(url_boletin, accept="text/html")
    _debug("boc_sumario.html", html, data_dir)
    sec, org, sub, out = None, "", "", []
    pend = None
    for b in bloques(html):
        cls = b["cls"]
        if "spanH5" in cls or "titulo2" in cls:
            n = norm(b["text"])
            sec = b["text"] if SECCIONES.search(n) else None
            org = sub = ""
            continue
        if sec is None:
            continue
        if "spanH4" in cls:
            org, sub = b["text"], ""
            continue
        if "spanH6" in cls:
            sub = b["text"]
            continue
        if b["tag"] == "p" and len(b["text"]) > 20:
            pend = b["text"]
            continue
        if b["tag"] != "a":
            continue
        for href, txt in b["links"]:
            if "idAnuBlob" in href and pend:
                m = ID_BOC.search(txt)
                out.append((pend, urllib.parse.urljoin(url_boletin, href), org + (f" · {sub}" if sub else ""),
                            m.group(0) if m else "", sec))
                pend = None
    vistos, res = set(), []  # un mismo enlace aparece en varios bloques anidados
    for t in out:
        if t[1] not in vistos:
            vistos.add(t[1])
            res.append(t)
    return res


def candidatos(fecha, data_dir=None, plantilla=None):
    out = []
    for ub in urls_boletin_del_dia(fecha, data_dir, plantilla):
        for titulo, url, org, idboc, sec in anuncios(ub, data_dir):
            if sec.startswith("2.3") and not SELECTIVO.search(norm(titulo)):
                continue
            m = re.search(r"idAnuBlob=(\d+)", url)
            out.append({
                "uid": "BOC:" + (idboc or ("anu" + m.group(1) if m else url[-60:])),
                "fuente": "BOC",
                "fecha_pub": fecha,
                "titulo": titulo + (f" [{idboc}]" if idboc else ""),
                "departamento": org.split(" · ")[0],
                "url": url,
                "url_pdf": url,
                "get_texto": (lambda u=url: fetch_text(u)),
                "fuente_zona": "cantabria",
            })
    return out
