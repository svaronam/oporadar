"""Convierte el HTML de un sumario en una lista ordenada de bloques (encabezados, párrafos, enlaces).

Los boletines autonómicos no tienen API, pero sus sumarios tienen siempre la misma forma:
sección (h4/h5/span) → organismo (h5/h6/span) → título (p/dt) → enlace al anuncio. Con esta lista
cada lector sólo tiene que decir qué etiquetas/clases son sección, organismo y título.
"""
import re
from html.parser import HTMLParser

INTERES = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "dt", "dd", "li", "ul", "span", "strong", "div"}


class _Bloques(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.pila = []  # bloques abiertos
        self._a = None
        self._skip = 0
        self._orden = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript"):
            self._skip += 1
            return
        if tag == "a":
            self._orden += 1
            self._a = [a.get("href") or "", [], self._orden]
            return
        if tag in INTERES:
            self._orden += 1
            self.pila.append({"tag": tag, "cls": a.get("class") or "", "id": a.get("id") or "", "txt": [],
                              "links": [], "orden": self._orden})

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a" and self._a is not None:
            href, txt, orden = self._a
            t = " ".join("".join(txt).split())
            for b in self.pila:
                b["links"].append((href, t))
                b["txt"].append(" " + "".join(txt) + " ")
            # cada enlace es también un bloque propio, en su sitio del documento
            self.out.append({"tag": "a", "cls": "", "id": "", "text": t, "links": [(href, t)], "orden": orden})
            self._a = None
            return
        if tag in INTERES:
            for i in range(len(self.pila) - 1, -1, -1):
                if self.pila[i]["tag"] == tag:
                    b = self.pila.pop(i)
                    b["text"] = " ".join("".join(b.pop("txt")).split())
                    self.out.append(b)
                    break

    def handle_data(self, d):
        if self._skip:
            return
        if self._a is not None:
            self._a[1].append(d)
        else:
            for b in self.pila:  # el texto cuenta para todos los bloques que lo contienen (p > strong)
                b["txt"].append(d)


def bloques(html):
    p = _Bloques()
    p.feed(html)
    p.close()
    while p.pila:  # etiquetas sin cerrar
        b = p.pila.pop()
        b["text"] = " ".join("".join(b.pop("txt")).split())
        p.out.append(b)
    p.out.sort(key=lambda b: b["orden"])
    return p.out


def capitalizar(s):
    menores = {"de", "del", "la", "las", "los", "el", "y", "e", "para", "en", "a"}
    pal = (s or "").lower().split()
    def cap(w):
        if w.startswith("(") and len(w) > 1:
            return "(" + w[1].upper() + w[2:]
        return w[:1].upper() + w[1:]
    return " ".join(p if (i and p in menores) else cap(p) for i, p in enumerate(pal))


SELECTIVO = re.compile(r"plaza|convoca|bases|selectiv|oposici|concurso|bolsa|oferta de empleo|empleo publico|"
                       r"admitid|excluid|tribunal|aspirantes|provisi[oó]n|cubrir|ingreso|estabilizaci", re.I)
