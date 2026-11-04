"""Barrida completa con fuentes simuladas: reintentos, días sin publicar, alertas de salud."""
import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from oporadar import config, salud, scan  # noqa: E402
from oporadar.db import DB  # noqa: E402

HOY = dt.date(2026, 10, 28)  # miércoles


class FechaFija(dt.date):
    @classmethod
    def today(cls):
        return HOY


def cand(fuente, f, uid, titulo, texto="", falla=False):
    def get():
        if falla:
            raise OSError("timeout")
        return texto
    return {"uid": f"{fuente}:{uid}", "fuente": fuente, "fecha_pub": f, "titulo": titulo, "departamento": "",
            "url": f"https://x/{uid}", "url_pdf": None, "get_texto": get, "fuente_zona": None,
            "zona_defecto": "limitrofe"}


class T(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cfg = config.cargar(self.dir)
        self.cfg["pausa_entre_peticiones"] = 0
        self.db = DB(os.path.join(self.dir, "t.db"))
        scan.dt.date = FechaFija
        self.llamadas = []
        self.fallar_texto = True
        self.bocyl_roto = False

        def boe_(f):
            self.llamadas.append(("BOE", f))
            if f.weekday() == 6:
                return []
            return [cand("BOE", f, f"g{f.day}", "Resolución por la que se convoca proceso selectivo para ingreso en el "
                         "Cuerpo de Gestión de Sistemas e Informática de la Administración del Estado.",
                         "mediante el sistema de oposición")]

        def bopa_(f):
            self.llamadas.append(("BOPA", f))
            if f == HOY:
                return []  # hoy aún no ha salido
            return [cand("BOPA", f, f"p{f.day}", "Resolución del Ayuntamiento de Gijón referente a la convocatoria para "
                         "proveer varias plazas.", "", falla=self.fallar_texto and f == HOY - dt.timedelta(days=1))]

        def bocyl_(f):
            self.llamadas.append(("BOCYL", f))
            if self.bocyl_roto:
                raise RuntimeError("HTTP 500")
            return []

        scan.boe.candidatos = boe_
        scan.bopa.candidatos = bopa_
        scan.bocyl.candidatos = bocyl_
        scan.boc.candidatos = lambda f, *a, **k: []
        scan.bopv.candidatos_por_fecha = lambda desde: {}

    def test_reintentos(self):
        scan.barrida(self.db, self.cfg, dias=4)
        ok = {(e["fuente"], e["fecha"]): e["ok"] for e in self.db.ultimos_escaneos(100)}
        hoy, ayer = HOY.isoformat(), (HOY - dt.timedelta(days=1)).isoformat()
        self.assertEqual(ok[("BOE", hoy)], 1)
        self.assertEqual(ok[("BOPA", hoy)], 0)   # sin publicar todavía: se reintentará
        self.assertEqual(ok[("BOPA", ayer)], 0)  # un anuncio no se pudo leer
        self.assertEqual(ok[("BOPA", (HOY - dt.timedelta(days=2)).isoformat())], 1)
        # segunda barrida: sólo repite lo pendiente
        self.llamadas.clear()
        self.fallar_texto = False
        scan.barrida(self.db, self.cfg, dias=4)
        self.assertIn(("BOPA", HOY - dt.timedelta(days=1)), self.llamadas)
        self.assertIn(("BOPA", HOY), self.llamadas)
        self.assertNotIn(("BOPA", HOY - dt.timedelta(days=2)), self.llamadas)
        self.assertNotIn(("BOE", HOY - dt.timedelta(days=2)), self.llamadas)
        ok = {(e["fuente"], e["fecha"]): e["ok"] for e in self.db.ultimos_escaneos(100)}
        self.assertEqual(ok[("BOPA", ayer)], 1)
        gsi = [i for i in self.db.listar() if i["fuente"] == "BOE"]
        self.assertTrue(gsi and gsi[0]["grupos"] == ["A2"])

    def test_alerta_error(self):
        self.bocyl_roto = True
        scan.barrida(self.db, self.cfg, dias=2)
        al = self.db.alertas_recientes()
        self.assertTrue(any(a["fuente"] == "BOCYL" and "No consigo leer" in a["texto"] for a in al), al)
        n = len(al)
        scan.barrida(self.db, self.cfg, dias=2)  # mismo día: no se repite
        self.assertEqual(len(self.db.alertas_recientes()), n)

    def test_alerta_vacia(self):
        # BOCYL devuelve 0 anuncios varios días laborables seguidos → posible cambio de web
        scan.barrida(self.db, self.cfg, dias=10)
        al = [a for a in self.db.alertas_recientes() if a["fuente"] == "BOCYL"]
        self.assertTrue(al and "días laborables" in al[0]["texto"], al)
        self.assertFalse([a for a in self.db.alertas_recientes() if a["fuente"] == "BOE"])

    def test_salud_sin_datos(self):
        self.assertEqual(salud.revisar(self.db, HOY), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
