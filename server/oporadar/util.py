"""Utilidades: normalización de texto, descargas HTTP y extracción de texto de HTML/PDF."""
import gzip
import re
import shutil
import ssl
import subprocess
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from html.parser import HTMLParser

# Certificados: en Windows, Python no ve las raíces que el sistema descarga bajo demanda (FNMT, Izenpe... que usan
# el BOPA o el BOPV) y falla con "self-signed certificate in certificate chain". `truststore` hace que Python verifique
# con el propio almacén del sistema, igual que el navegador. Si no está, se intenta con `certifi`. Nunca se desactiva
# la verificación.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:  # en la Pi no hace falta: Debian ya trae esas raíces
    pass

UA = "OpoRadar/1.0 (+uso personal; vigilancia de convocatorias publicas)"


def norm(s: str) -> str:
    """minúsculas, sin tildes, espacios colapsados, guiones de 'concurso-oposición' unificados."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("­", "")
    s = re.sub(r"[‐-―]", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def decodificar(data: bytes, ctype: str = "") -> str:
    """Texto con la codificación correcta: cabecera HTTP, <meta charset>, <?xml encoding?> o, si nada,
    UTF-8 estricto y si falla ISO-8859-1 (el BOPV, por ejemplo, va en ISO-8859-1)."""
    m = re.search(r"charset=[\"']?([\w-]+)", ctype or "", re.I)
    cand = [m.group(1)] if m else []
    cabeza = data[:3000].decode("ascii", errors="ignore")
    for rx in (r"<meta[^>]+charset=[\"']?([\w-]+)", r"<\?xml[^>]+encoding=[\"']([\w-]+)"):
        mm = re.search(rx, cabeza, re.I)
        if mm:
            cand.append(mm.group(1))
    for cs in cand + ["utf-8"]:
        try:
            return data.decode(cs)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("cp1252", errors="replace")


def _ctx_certifi():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def _abrir(url, data, accept, timeout, binary, ctx=None):
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET", headers={
        "User-Agent": UA, "Accept": accept, "Accept-Encoding": "gzip", "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        ctype = r.headers.get("Content-Type", "")
        if binary:
            return raw, ctype
        return decodificar(raw, ctype), ctype


def fetch(url: str, accept: str = "*/*", timeout: int = 40, retries: int = 2, binary: bool = False, data=None):
    """GET (o POST si se pasa data=b'...'). Reintenta errores de red; los 404 se propagan al momento."""
    last = None
    for i in range(retries + 1):
        try:
            return _abrir(url, data, accept, timeout, binary)
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                raise
            last = e
        except urllib.error.URLError as e:
            if isinstance(e.reason, ssl.SSLCertVerificationError):
                ctx = _ctx_certifi()
                if ctx is not None:
                    try:
                        return _abrir(url, data, accept, timeout, binary, ctx)
                    except Exception as e2:
                        last = e2
                        break
                last = e
                break  # un certificado no se arregla reintentando
            last = e
        except Exception as e:  # red, timeout...
            last = e
        time.sleep(2 * (i + 1))
    raise last


class _TextParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "head"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "td", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)


def html_to_text(html: str) -> str:
    p = _TextParser()
    p.feed(html)
    txt = "".join(p.out)
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    return re.sub(r"\n\s*\n+", "\n", txt).strip()


class _PorId(HTMLParser):
    VACIAS = {"br", "img", "hr", "input", "meta", "link", "area", "base", "col", "source", "wbr"}

    def __init__(self, ident):
        super().__init__(convert_charrefs=False)
        self.ident, self.prof, self.ini, self.fin = ident, 0, None, None

    def handle_starttag(self, tag, attrs):
        if tag in self.VACIAS:
            return
        if self.ini is None:
            if dict(attrs).get("id") == self.ident:
                self.ini, self.prof = self.getpos(), 1
        elif self.fin is None:
            self.prof += 1

    def handle_endtag(self, tag):
        if tag in self.VACIAS or self.ini is None or self.fin is not None:
            return
        self.prof -= 1
        if self.prof == 0:
            self.fin = self.getpos()


def extraer_por_id(html: str, ident: str) -> str:
    """HTML del elemento con ese id (para quedarnos con el artículo y no con menús ni scripts)."""
    p = _PorId(ident)
    try:
        p.feed(html)
    except Exception:
        pass
    if p.ini is None:
        return ""
    lineas = html.splitlines(keepends=True)

    def off(pos):
        return sum(len(x) for x in lineas[:pos[0] - 1]) + pos[1]
    a = off(p.ini)
    b = off(p.fin) if p.fin else len(html)
    return html[a:b]


def pdf_to_text(data: bytes) -> str:
    """pdftotext (poppler-utils, en la Pi) o, si no está, pypdf (pip install pypdf, lo usa el .bat en Windows)."""
    exe = shutil.which("pdftotext")
    if not exe:
        try:
            import io
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in r.pages[:6])
        except Exception:
            return ""
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        try:
            r = subprocess.run([exe, "-layout", "-l", "6", f.name, "-"], capture_output=True, timeout=60)
            return r.stdout.decode("utf-8", errors="replace")
        except Exception:
            return ""


def fetch_text(url: str) -> str:
    """Descarga una página o PDF y devuelve su texto plano."""
    data, ctype = fetch(url, binary=True)
    if "pdf" in ctype.lower() or data[:5] == b"%PDF-":
        return pdf_to_text(data)
    return html_to_text(decodificar(data, ctype))
