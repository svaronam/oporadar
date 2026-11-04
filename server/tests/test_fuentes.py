"""Prueba los lectores de BOE y BOC con respuestas simuladas (sin red)."""
import datetime as dt
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from oporadar.sources import boe  # noqa: E402

SUMARIO = {"status": {"code": "200"}, "data": {"sumario": {"metadatos": {}, "diario": [{
    "numero": "258",
    "seccion": [
        {"codigo": "1", "nombre": "I. Disposiciones generales", "departamento": []},
        {"codigo": "2B", "nombre": "II. Autoridades y personal. - B. Oposiciones y concursos", "departamento": [
            {"codigo": "1", "nombre": "ADMINISTRACIÓN LOCAL", "epigrafe": {"nombre": "Personal funcionario y laboral", "item": [
                {"identificador": "BOE-A-2026-22001", "titulo": "Resolución de 14 de octubre de 2026, del Ayuntamiento de Camargo (Cantabria), referente a la convocatoria para proveer varias plazas.",
                 "url_pdf": {"szBytes": "1", "texto": "https://www.boe.es/boe/dias/2026/10/26/pdfs/BOE-A-2026-22001.pdf"},
                 "url_html": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-22001",
                 "url_xml": "https://www.boe.es/diario_boe/xml.php?id=BOE-A-2026-22001"},
            ]}},
            {"codigo": "2", "nombre": "UNIVERSIDADES", "epigrafe": [{"nombre": "Personal de administración", "item":
                {"identificador": "BOE-A-2026-22002", "titulo": "Resolución de la Universidad de Oviedo, por la que se convocan pruebas selectivas para ingreso en la Escala de Técnicos Auxiliares de Informática.",
                 "url_html": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-22002"}}]},
        ]},
    ]}]}}}

XML = """<?xml version="1.0" encoding="utf-8"?><documento><metadatos/><texto>
<p>En el «Boletín Oficial de Cantabria» número 198 se han publicado las bases para proveer una plaza de Técnico Informático, Subgrupo A2, mediante oposición libre, como funcionario de carrera.</p>
<p>El plazo de presentación de solicitudes será de veinte días naturales.</p></texto></documento>"""


class TBoe(unittest.TestCase):
    def test_sumario(self):
        def fake(url, **kw):
            if "sumario" in url:
                return json.dumps(SUMARIO), "application/json"
            return XML, "application/xml"
        boe.fetch = fake
        cs = boe.candidatos(dt.date(2026, 10, 26))
        self.assertEqual(len(cs), 2)
        self.assertEqual(cs[0]["departamento"], "ADMINISTRACIÓN LOCAL")
        self.assertTrue(cs[0]["url_pdf"].endswith(".pdf"))
        self.assertIn("Técnico Informático", cs[0]["get_texto"]())
        self.assertIn("22002", cs[1]["get_texto"].__defaults__[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
