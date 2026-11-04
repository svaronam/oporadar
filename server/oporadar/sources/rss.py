"""Fuentes RSS/Atom genéricas definidas en config.json -> "rss": [{"nombre","url","zona"}].

Sirve para añadir boletines o portales de empleo (otra comunidad, la web de una universidad...) que publiquen RSS.
Sólo se miran las entradas publicadas en los últimos días (config "dias_atras").
"""
import datetime as dt
import email.utils
import re
import xml.etree.ElementTree as ET

from ..util import fetch, fetch_text, html_to_text


def _fecha(s):
    if not s:
        return None
    try:
        return email.utils.parsedate_to_datetime(s).date()
    except Exception:
        pass
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def candidatos(fuente, desde: dt.date):
    txt, _ = fetch(fuente["url"], accept="application/rss+xml, application/atom+xml, text/xml")
    root = ET.fromstring(txt.encode("utf-8"))
    out = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entradas = root.findall(".//item") or root.findall(".//a:entry", ns)
    for e in entradas:
        def g(tag):
            n = e.find(tag) if not tag.startswith("a:") else e.find(tag, ns)
            return (n.text or "").strip() if n is not None and n.text else ""
        titulo = g("title") or g("a:title")
        link = g("link")
        if not link:
            ln = e.find("a:link", ns)
            link = ln.get("href") if ln is not None else ""
        desc = html_to_text(g("description") or g("a:summary") or g("a:content"))
        f = _fecha(g("pubDate") or g("a:updated") or g("a:published")) or dt.date.today()
        if f < desde:
            continue
        out.append({
            "uid": f"RSS:{fuente['nombre']}:{link or titulo}"[:300],
            "fuente": fuente["nombre"],
            "fecha_pub": f,
            "titulo": titulo,
            "departamento": fuente.get("organismo", ""),
            "url": link,
            "url_pdf": None,
            "texto_inicial": desc,
            "get_texto": (lambda u=link, d=desc: (d + "\n" + fetch_text(u)) if u else d),
            "fuente_zona": fuente.get("zona"),
        })
    return out
