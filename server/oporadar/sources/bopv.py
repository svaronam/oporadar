"""BOPV · Boletín Oficial del País Vasco, «Autoridades y personal · Oposiciones y concursos».

Verificado contra la web real (oct. 2026):
- Último sumario: https://www.euskadi.eus/web01-bopv/es/bopv2/datos/Ultimo.shtml (enlaza su PDF AAAA/MM/sAA_NNNN.pdf)
- Sumario de un número: .../bopv2/datos/AAAA/MM/sAA_NNNN.shtml (NNNN correlativo en el año)
- <h5 class="BOPVSumarioSubSeccion">Oposiciones y concursos</h5>, <h5 class="BOPVSumarioOrganismo">,
  <p class="BOPVSumarioTitulo"><a href="AAAA/MM/AANNNNNa.shtml">título</a>
- Codificado en ISO-8859-1 (util.decodificar lo detecta).
Incluye Gobierno Vasco, Osakidetza, IVAP, UPV/EHU y ayuntamientos y diputaciones vascas.
"""
import datetime as dt
import re
import urllib.error
import urllib.parse

from ..util import fetch, fetch_text, html_to_text, norm
from .bloques import bloques, capitalizar

BASE = "https://www.euskadi.eus/web01-bopv/es/bopv2/datos/"
MESES = {m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                     "septiembre", "octubre", "noviembre", "diciembre"], 1)}
_cache = {}  # (año, número) -> (fecha, url)


CABECERA = re.compile(r"sumario n\.?\s*[ºo]?\s*(\d+)\s*,\s*\w+\s+(\d{1,2}) de (\w+) de (\d{4})")


def _cabecera(html):
    """(número, fecha) de «Sumario n.º 201 , miércoles 21 de octubre de 2026», o (None, None)."""
    m = CABECERA.search(norm(html_to_text(html)))
    if m and m.group(3) in MESES:
        return int(m.group(1)), dt.date(int(m.group(4)), MESES[m.group(3)], int(m.group(2)))
    return None, None


def _ultimo():
    html, _ = fetch(BASE + "Ultimo.shtml", accept="text/html")
    m = re.search(r"(\d{4})/(\d{2})/s(\d{2})_(\d{4})\.(?:pdf|epub|shtml)", html)
    if not m:
        raise RuntimeError("No encuentro el número del último BOPV (¿ha cambiado la web?)")
    return int(m.group(1)), int(m.group(2)), int(m.group(4))


def _sumario(anio, numero, mes_aprox):
    """Busca el sumario nº `numero` probando la carpeta del mes aproximado y las dos anteriores."""
    if (anio, numero) in _cache:
        return _cache[(anio, numero)]
    for k in range(0, 3):
        mes = mes_aprox - k
        a = anio
        if mes < 1:
            mes, a = mes + 12, anio - 1
        if a != anio:
            break
        url = f"{BASE}{anio}/{mes:02d}/s{anio % 100:02d}_{numero:04d}.shtml"
        try:
            html, _ = fetch(url, accept="text/html", retries=0)
        except urllib.error.HTTPError:
            continue
        num, fecha = _cabecera(html)
        # una carpeta de mes equivocada también responde 200, pero sin sumario: hay que comprobarlo
        if "BOPVSumario" not in html or num != numero:
            continue
        res = (fecha, url, html, mes)
        _cache[(anio, numero)] = res
        return res
    return None


def sumarios_desde(desde: dt.date):
    """[(fecha, url, html)] de los boletines publicados desde `desde` (incluido) hasta hoy."""
    anio, mes, num = _ultimo()
    out = []
    while num >= 1:
        r = _sumario(anio, num, mes)
        if r is None:
            break
        f, url, html, mes = r
        if f and f < desde:
            break
        out.append((f, url, html))
        num -= 1
        if len(out) > 40:
            break
    return out


def anuncios(url, html):
    out, en_opos, org = [], False, ""
    for b in bloques(html):
        cls = b["cls"]
        if "BOPVSumarioSeccion" in cls:
            if b["text"].strip():
                en_opos = False
            continue
        if "BOPVSumarioSubSeccion" in cls:
            en_opos = "oposiciones y concursos" in norm(b["text"])
            continue
        if not en_opos:
            continue
        if "BOPVSumarioOrganismo" in cls:
            org = capitalizar(b["text"])
            continue
        if "BOPVSumarioTitulo" in cls and b["links"]:
            href, txt = b["links"][0]
            # en Ultimo.shtml los enlaces son "AAAA/MM/xxx.shtml" relativos a /datos/
            absu = BASE + href if re.match(r"^\d{4}/\d{2}/", href) else urllib.parse.urljoin(url, href)
            out.append((txt or b["text"], absu, org))
    return out


def candidatos_por_fecha(desde: dt.date):
    """{fecha: [candidatos]} desde `desde`. El BOPV se recorre por número, no por fecha."""
    res = {}
    for f, url, html in sumarios_desde(desde):
        lista = res.setdefault(f, [])
        for titulo, u, org in anuncios(url, html):
            m = re.search(r"/(\d{7,8}a?)\.shtml", u)
            lista.append({
                "uid": "BOPV:" + (m.group(1) if m else u[-40:]),
                "fuente": "BOPV",
                "fecha_pub": f,
                "titulo": titulo,
                "departamento": org,
                "url": u,
                "url_pdf": u.replace(".shtml", ".pdf"),
                "get_texto": (lambda x=u: fetch_text(x)),
                "fuente_zona": None,
                "zona_defecto": "limitrofe",
            })
    return res
