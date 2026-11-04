"""BOCYL · Boletín Oficial de Castilla y León, «B. Autoridades y personal: B.2. Oposiciones y Concursos».

Verificado contra la web real (oct. 2026):
- Sumario por fecha: https://bocyl.jcyl.es/boletin.do?fechaBoletin=DD/MM/AAAA
- Sección: <h4 class="encabezado4">B. AUTORIDADES Y PERSONAL: B.2. Oposiciones y Concursos</h4>
  organismo <h5 class="encabezado6">, título <p>, y enlaces al PDF (boletines/AAAA/MM/DD/pdf/BOCYL-D-...pdf)
  y a la versión HTML (html/AAAA/MM/DD/html/BOCYL-D-....do), que es la que leemos.
- Cubre Junta de Castilla y León, sus universidades (León, Burgos, Valladolid, Salamanca) y la sección III
  (Administración local), que también se revisa filtrando por palabras de procesos selectivos.
"""
import re
import urllib.error
import urllib.parse

from ..util import fetch, fetch_text, norm
from .bloques import SELECTIVO, bloques, capitalizar

BASE = "https://bocyl.jcyl.es/"
CV = re.compile(r"BOCYL-D-\d{8}-\d+(?:-\d+)?")


def candidatos(fecha):
    url = f"{BASE}boletin.do?fechaBoletin={fecha:%d/%m/%Y}"
    try:
        html, _ = fetch(url, accept="text/html")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    if fecha.strftime("%d%m%Y") not in html:  # día sin boletín: la web devuelve otra página
        return []
    out, sec, org, pend, local = [], None, "", None, False
    for b in bloques(html):
        if b["tag"] == "h4":
            n = norm(b["text"])
            if "encabezado4_sinlinea" in b["cls"] and re.search(r"disposiciones y actos", n):
                local = True  # sección III. Administración local
            sec = b["text"] if ("oposiciones y concursos" in n or local and "disposiciones y actos" in n) else None
            continue
        if sec is None:
            continue
        if b["tag"] == "h5":
            org = capitalizar(b["text"])
            continue
        if b["tag"] == "p" and len(b["text"]) > 30:
            pend = b["text"]
            continue
        if b["tag"] == "ul":
            pdf = next((h for h, _ in b["links"] if h.endswith(".pdf")), None)
            htm = next((h for h, _ in b["links"] if "/html/" in h and h.endswith(".do")), None)
            if pend and (pdf or htm):
                if local and not SELECTIVO.search(norm(pend)):
                    pend = None
                    continue
                m = CV.search((pdf or "") + (htm or ""))
                u_html = urllib.parse.urljoin(BASE, htm) if htm else None
                u_pdf = urllib.parse.urljoin(BASE, pdf) if pdf else None
                out.append({
                    "uid": "BOCYL:" + (m.group(0) if m else (u_pdf or u_html)[-60:]),
                    "fuente": "BOCYL",
                    "fecha_pub": fecha,
                    "titulo": pend,
                    "departamento": org,
                    "url": u_html or u_pdf,
                    "url_pdf": u_pdf,
                    "get_texto": (lambda u=u_html or u_pdf: fetch_text(u)),
                    "fuente_zona": None,  # se deduce del organismo (Junta → limítrofe, Ayto. de Soria → cercana...)
                    "zona_defecto": "limitrofe",
                })
                pend = None
    vistos, res = set(), []
    for c in out:
        if c["uid"] not in vistos:
            vistos.add(c["uid"])
            res.append(c)
    return res
