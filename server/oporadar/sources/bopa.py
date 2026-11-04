"""BOPA · Boletín Oficial del Principado de Asturias.

Verificado contra la web real (oct. 2026):
- Sumario por fecha:
  https://miprincipado.asturias.es/bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb
     &p_p_lifecycle=0&p_r_p_summaryDate=DD/MM/AAAA&p_r_p_summaryIsSearch=false
- Dentro de <div id="bopa-boletin">: <h4> sección (I. Principado de Asturias, IV. Administración Local...),
  <h5> subsección (AUTORIDADES Y PERSONAL...), <h6> organismo, <dl><dt>título [Cód. 2026-08468]</dt>
  <dd> enlace «Texto de la disposición» (HTML, el texto está en #bopa-articulo) y PDF /bopa/AAAA/MM/DD/COD.pdf
- Leemos «I · Autoridades y personal» entero y, de «IV · Administración local», lo que suene a proceso selectivo
  (ahí salen las bases de Gijón, Oviedo, Avilés, Siero... antes que el extracto del BOE).
"""
import re
import urllib.parse

from ..util import extraer_por_id, fetch, html_to_text, norm
from .bloques import SELECTIVO, bloques, capitalizar

BASE = "https://miprincipado.asturias.es/"
SUMARIO = (BASE + "bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb&p_p_lifecycle=0"
           "&p_r_p_summaryDate={f}&p_r_p_summaryIsSearch=false")
COD = re.compile(r"\[\s*C[óo]d\.\s*(\d{4}-\d+)\s*\]")


def texto(url):
    html, _ = fetch(url, accept="text/html")
    return html_to_text(extraer_por_id(html, "bopa-articulo") or html)


def candidatos(fecha):
    html, _ = fetch(SUMARIO.format(f=f"{fecha:%d/%m/%Y}"), accept="text/html")
    i = html.find('id="bopa-boletin"')
    if i < 0:
        return []  # ese día no hubo BOPA
    html = html[i:]
    out, sec, sub, org, pend = [], "", "", "", None
    for b in bloques(html):
        t, n = b["tag"], norm(b["text"])
        if t == "h4":
            sec, sub, org = n, "", ""
            continue
        if t == "h5":
            sub, org = n, ""
            if sec.startswith("iv"):
                org = capitalizar(b["text"])
            continue
        if t == "h6":
            nombre = capitalizar(b["text"])
            org = ("Ayuntamiento " + nombre[0].lower() + nombre[1:]) if (sec.startswith("iv") and n.startswith("de ")) \
                else nombre
            continue
        en_personal = sec.startswith("i.") and "autoridades y personal" in sub
        en_local = sec.startswith("iv")
        if not (en_personal or en_local):
            continue
        if t == "dt":
            pend = b["text"].replace("\xa0", " ")
            continue
        if t == "dd" and pend:
            m = COD.search(pend)
            titulo = COD.sub("", pend).strip()
            if en_local and not SELECTIVO.search(norm(titulo)):
                pend = None
                continue
            u_txt = next((h for h, x in b["links"] if "disposiciones" in h), None)
            u_pdf = next((h for h, x in b["links"] if h.endswith(".pdf")), None)
            u_txt = urllib.parse.urljoin(BASE, u_txt) if u_txt else None
            u_pdf = urllib.parse.urljoin(BASE, u_pdf) if u_pdf else None
            out.append({
                "uid": "BOPA:" + (m.group(1) if m else (u_pdf or u_txt or titulo)[-60:]),
                "fuente": "BOPA",
                "fecha_pub": fecha,
                "titulo": titulo + (f" [Cód. {m.group(1)}]" if m else ""),
                "departamento": org,
                "url": u_txt or u_pdf,
                "url_pdf": u_pdf,
                "get_texto": (lambda u=u_txt: texto(u) if u else ""),
                "fuente_zona": None,
                "zona_defecto": "limitrofe",
            })
            pend = None
    return out
