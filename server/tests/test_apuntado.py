"""Vigilancia de páginas de convocatorias apuntadas y enlace automático con BOE/BOC (sin red)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from oporadar import vigilar  # noqa: E402
from oporadar.db import DB  # noqa: E402

PAG = """<html><head><title>Portal de transparencia - Tarazona</title></head><body>
<header><a href="/">Inicio</a><a href="/tramites">Trámites</a></header>
<nav><a href="/publicidad">Publicidad</a></nav>
<main>
<p>1. INSTITUCIONAL/1.7. PERSONAL/1.7.3 PROCESOS SELECTIVOS/2026/TECNICO DE INFORMATICA</p>
<table>
<tr><td><a href="/transparency/16e4/doc1/?sid=abc123">Convocatoria proceso selectivo BOE-A-2026-20186</a></td></tr>
<tr><td><a href="/transparency/16e4/doc2/">Bases proceso selectivo bop_6324_2026</a></td></tr>
<tr><td><a href="/transparency/16e4/doc3/">ANEXO II</a></td></tr>
{extra}
</table></main>
<footer><a href="/aviso-legal">Aviso legal</a><a href="/cookies">Política de cookies</a></footer>
</body></html>"""


class T(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.db = DB(os.path.join(d, "t.db"))
        self.iid = self.db.crear_manual("Técnico de Informática", "Ayuntamiento de Tarazona", ["A2"], "Tarazona", 280,
                                        "resto", "https://tarazona.sedelectronica.es/transparency/16e4/")

    def test_documentos(self):
        docs, titulo = vigilar.documentos("https://tarazona.sedelectronica.es/transparency/16e4/", PAG.format(extra=""))
        textos = [t for _, t, _ in docs]
        self.assertEqual(len(docs), 3, textos)
        self.assertIn("ANEXO II", textos)
        self.assertNotIn("Aviso legal", textos)
        self.assertNotIn("sid=", docs[0][0])  # parámetro volátil fuera de la clave

    def test_primera_vez_sin_aviso_y_luego_novedad(self):
        url = "https://tarazona.sedelectronica.es/transparency/16e4/"
        vid = self.db.add_vigilancia(self.iid, url)
        html = [PAG.format(extra="")]
        vigilar.fetch = lambda u, **k: (html[0], "text/html")
        self.assertEqual(vigilar.revisar(self.db, self.db.vigilancia(vid)), 0)
        self.assertEqual(self.db.novedades_desde(0), [])  # los 3 iniciales no notifican
        # mismo contenido con otro sid: nada nuevo
        html[0] = PAG.format(extra="").replace("sid=abc123", "sid=zzz999")
        self.assertEqual(vigilar.revisar(self.db, self.db.vigilancia(vid)), 0)
        # aparece la lista de admitidos
        html[0] = PAG.format(extra='<tr><td><a href="/transparency/16e4/doc9/">Lista provisional de admitidos y excluidos</a></td></tr>')
        self.assertEqual(vigilar.revisar(self.db, self.db.vigilancia(vid)), 1)
        nov = self.db.novedades_desde(0)
        self.assertEqual(len(nov), 1)
        self.assertIn("admitidos", nov[0]["titulo"])
        ap = self.db.apuntadas()[0]
        self.assertEqual(ap["sin_leer"], 1)
        self.assertEqual(len(ap["novedades"]), 4)
        self.assertEqual(self.db.contar()["_sin_leer"], 1)

    def test_enlace_boe(self):
        item = {"uid": "BOE:X", "fuente": "BOE", "organismo": "Ayuntamiento de Tarazona (Zaragoza)", "tipo": "seguimiento",
                "titulo": "Resolución por la que se aprueba la lista de admitidos de Técnico de Informática",
                "url": "https://www.boe.es/x", "url_pdf": None}
        self.assertEqual(vigilar.enlazar_con_apuntadas(self.db, item), 1)
        self.assertEqual(len(self.db.novedades_desde(0)), 1)
        otro = dict(item, uid="BOE:Y", organismo="Ayuntamiento de Laredo (Cantabria)", url="https://www.boe.es/y")
        self.assertEqual(vigilar.enlazar_con_apuntadas(self.db, otro), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
