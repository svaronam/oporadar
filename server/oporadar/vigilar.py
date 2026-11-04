"""Vigila las páginas de las convocatorias a las que estás apuntado y detecta documentos nuevos.

Funciona con cualquier web que liste los documentos como enlaces (sedes electrónicas tipo
xxx.sedelectronica.es, portales de empleo de ayuntamientos y universidades, páginas de BOE/BOP...).
La primera vez guarda los documentos que ya hay (aparecen en la ficha, sin aviso); a partir de ahí,
cada enlace nuevo es una novedad con notificación.
"""
import logging
import os
import re
import time
import urllib.parse
from html.parser import HTMLParser

from .util import fetch, norm

log = logging.getLogger("oporadar")

DOC_HREF = re.compile(r"\.(pdf|docx?|odt|xlsx?|ods|zip|rtf)(\?|#|$)|download|descarga|/document|documento|fichero|"
                      r"/file|getfile|adjunto|anexo|blob|verdocumento|/doc/|csv=|idanublob|/boe/dias/|boe\.es/diario_boe|"
                      r"/bop|bocyl|bopa|boc\.cantabria|/dogc|/bopv|/boja", re.I)
DOC_TXT = re.compile(r"\bboe\b|\bbop\w*|\bboc\w*|\bbocyl|anexo|bases|convocatoria|lista|admitid|excluid|resoluci|decreto|"
                     r"anuncio|correcci|rectifica|tribunal|calificaci|examen|ejercicio|prueba|plantilla|nombramiento|"
                     r"aprobad|puntuaci|baremo|cuestionario|respuestas|acta|citaci|fecha|lugar|modelo|solicitud|"
                     r"instancia|temario|programa|propuesta|alegaci|revisi|definitiv|provisional|\.pdf", re.I)
VOLATIL = re.compile(r"^(jsessionid|sid|token|t|ts|_|cache|rnd|random|time|csrf\w*|__\w+)$", re.I)


class _Links(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self._a, self._txt, self._skip = [], None, [], 0
        self.titulo, self._en_title = "", False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        if tag == "title":
            self._en_title = True
        if tag == "a" and not self._skip:
            a = dict(attrs)
            self._a = (a.get("href") or "", a.get("title") or "", a.get("download"))
            self._txt = []

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag == "title":
            self._en_title = False
        if tag == "a" and self._a is not None:
            href, title, dl = self._a
            self.links.append((href, " ".join("".join(self._txt).split()) or title, dl is not None))
            self._a = None

    def handle_data(self, d):
        if self._en_title:
            self.titulo += d
        if self._a is not None:
            self._txt.append(d)


def _clave(url, texto):
    u = urllib.parse.urlsplit(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True) if not VOLATIL.match(k)]
    limpio = urllib.parse.urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip("/"), urllib.parse.urlencode(sorted(q)), ""))
    return limpio


def documentos(url, html):
    """[(clave, texto, url_absoluta)] de los enlaces que parecen documentos o anuncios del proceso."""
    p = _Links()
    p.feed(html)
    base = urllib.parse.urlsplit(url)
    out, vistos = [], set()
    for href, texto, es_descarga in p.links:
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absu = urllib.parse.urljoin(url, href)
        u = urllib.parse.urlsplit(absu)
        if u.scheme not in ("http", "https"):
            continue
        if absu.split("#")[0].rstrip("/") == url.split("#")[0].rstrip("/"):
            continue
        t = texto.strip()
        es_doc = es_descarga or bool(DOC_HREF.search(absu)) or (len(t) >= 6 and bool(DOC_TXT.search(t)))
        # en la misma web, enlaces a subpáginas con texto largo (p. ej. "Lista provisional de admitidos")
        if not es_doc and u.netloc == base.netloc and len(t) > 25 and u.path.startswith(base.path.rsplit("/", 2)[0]):
            es_doc = True
        if not es_doc:
            continue
        clave = _clave(absu, t)
        if clave in vistos:
            continue
        vistos.add(clave)
        out.append((clave, t or os.path.basename(u.path) or absu, absu))
    return out, " ".join(p.titulo.split())


def revisar(db, vig, data_dir=None):
    """Revisa una página vigilada. Devuelve nº de documentos nuevos (0 la primera vez)."""
    vid, item_id, url = vig["id"], vig["item_id"], vig["url"]
    primera = not vig.get("ultimo_check")
    try:
        html, ctype = fetch(url, accept="text/html,application/xhtml+xml,*/*")
        if data_dir:
            d = os.path.join(data_dir, "debug")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"vigilancia_{vid}.html"), "w", encoding="utf-8") as f:
                f.write(html)
        if "html" not in ctype.lower() and "<a" not in html[:20000].lower():
            # la URL es directamente un PDF u otro fichero: lo tratamos como un único documento
            docs, titulo = [(_clave(url, ""), os.path.basename(urllib.parse.urlsplit(url).path) or url, url)], ""
        else:
            docs, titulo = documentos(url, html)
        if vig.get("nombre") in (None, "") and titulo:
            with db.lock, db._c() as c:
                c.execute("UPDATE vigilancias SET nombre=? WHERE id=?", (titulo[:120], vid))
        conocidas = db.claves_docs(vid)
        nuevos = 0
        for clave, texto, u in docs:
            if clave in conocidas:
                continue
            db.add_doc(vid, clave, texto, u)
            nid = db.add_novedad(item_id, "web", texto, u, inicial=primera)
            if nid and not primera:
                nuevos += 1
                log.info("Documento nuevo en vigilancia %s: %s", vid, texto[:100])
        error = None
        if not docs:
            error = ("No veo documentos en esta página. Si se ven en el navegador, puede que la web los cargue con "
                     "JavaScript: prueba con la URL de la carpeta/listado concreto.")
        db.fin_vigilancia(vid, True, len(docs), error)
        return nuevos
    except Exception as e:
        log.warning("Vigilancia %s (%s) falló: %s", vid, url, e)
        db.fin_vigilancia(vid, False, vig.get("n_docs") or 0, str(e)[:250])
        return 0


def revisar_todas(db, data_dir=None, pausa=1.0):
    total = 0
    for v in db.vigilancias():
        total += revisar(db, v, data_dir)
        time.sleep(pausa)
    return total


# ------------------------------------------------------------------ BOE/BOC -> apuntadas
def clave_organismo(org):
    n = norm(org or "")
    n = re.sub(r"\([^)]*\)", " ", n)
    n = re.sub(r"\b(excmo|ilmo|m\.?\s*i\.?)\.?\s+", "", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return " ".join(n.split())


def enlazar_con_apuntadas(db, item_nuevo):
    """Si sale en BOE/BOC algo de informática del mismo organismo que una convocatoria apuntada
    (lista de admitidos, tribunal, extracto que abre plazo, corrección...), se añade como novedad."""
    k = clave_organismo(item_nuevo.get("organismo"))
    if not k:
        return 0
    n = 0
    for ap in db.apuntadas():
        if ap["uid"] == item_nuevo["uid"]:
            continue
        ka = clave_organismo(ap.get("organismo"))
        if ka and (ka == k or ka in k or k in ka):
            etiqueta = {"seguimiento": "Fase del proceso", "correccion": "Corrección", "convocatoria": "Convocatoria",
                        "oep": "Oferta de empleo"}.get(item_nuevo.get("tipo"), "Anuncio")
            if db.add_novedad(ap["id"], item_nuevo["fuente"], f"{etiqueta}: {item_nuevo['titulo']}",
                              item_nuevo.get("url_pdf") or item_nuevo["url"]):
                n += 1
    return n
