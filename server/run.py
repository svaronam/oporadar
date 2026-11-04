#!/usr/bin/env python3
"""OpoRadar — vigila boletines oficiales en busca de oposiciones de informática.

  python3 run.py servir                 arranca la web/API y la barrida diaria (lo que usa systemd)
  python3 run.py barrida [--dias N] [--forzar]   barrida manual (p. ej. --dias 30 la primera vez)
  python3 run.py probar [fuente] [AAAA-MM-DD]     muestra lo que encuentra cada boletín ese día, sin guardar
                                                 fuente: todas (por defecto), boe, boc, bocyl, bopa, bopv
  python3 run.py demo                            mete anuncios de ejemplo para ver la web/app sin esperar
"""
import argparse
import datetime as dt
import logging
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from oporadar import classify, config, scan, web  # noqa: E402
from oporadar.db import DB  # noqa: E402
from oporadar.sources import boc, bocyl, boe, bopa, bopv  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="OpoRadar")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("servir")
    b = sub.add_parser("barrida")
    b.add_argument("--dias", type=int, default=None)
    b.add_argument("--forzar", action="store_true", help="vuelve a revisar días ya revisados")
    p = sub.add_parser("probar")
    p.add_argument("fuente", nargs="?", default="todas", choices=["todas", "boe", "boc", "bocyl", "bopa", "bopv"])
    p.add_argument("fecha", nargs="?")
    sub.add_parser("demo")
    pl = sub.add_parser("puerto-libre")
    pl.add_argument("desde", type=int, nargs="?", default=8795)
    a = ap.parse_args()

    if a.cmd == "puerto-libre":  # lo usa ver_en_pc.bat: imprime el primer puerto libre
        import socket
        p = a.desde
        while True:
            s = socket.socket()
            try:
                s.bind(("127.0.0.1", p))
                s.close()
                print(p)
                return
            except OSError:
                p += 1

    cfg = config.cargar(BASE)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(os.path.join(cfg["data_dir"], "oporadar.log"), encoding="utf-8")])
    db = DB(os.path.join(cfg["data_dir"], "oporadar.db"))

    if a.cmd == "servir":
        web.servir(db, cfg)
    elif a.cmd == "barrida":
        n = scan.barrida(db, cfg, a.dias, a.forzar)
        print(f"\nNuevas: {n}")
    elif a.cmd == "probar":
        probar(cfg, a.fuente, dt.date.fromisoformat(a.fecha) if a.fecha else None)
    elif a.cmd == "demo":
        demo(db, cfg)


def probar(cfg, fuente, fecha):
    """Lee cada boletín sin guardar nada y enseña qué ve. Es la prueba de que los lectores funcionan."""
    if fecha is None:
        # de madrugada o en fin de semana los boletines de hoy aún no existen: probamos el último laborable completo
        fecha = dt.date.today()
        if dt.datetime.now().hour < 10:
            fecha -= dt.timedelta(days=1)
        while fecha.weekday() >= 5:
            fecha -= dt.timedelta(days=1)
    lectores = {
        "boe": lambda: boe.candidatos(fecha),
        "boc": lambda: boc.candidatos(fecha, cfg["data_dir"], cfg.get("boc_url_plantilla") or None),
        "bocyl": lambda: bocyl.candidatos(fecha),
        "bopa": lambda: bopa.candidatos(fecha),
        "bopv": lambda: bopv.candidatos_por_fecha(fecha).get(fecha, []),
    }
    nombres = list(lectores) if fuente == "todas" else [fuente]

    class FakeDB:
        def __init__(self):
            self.g = []

        def guardar(self, item):
            self.g.append(item)
            return True

        def apuntadas(self):
            return []

    resumen = []
    for n in nombres:
        print(f"\n===== {n.upper()} {fecha.isoformat()} =====")
        try:
            cands = lectores[n]()
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            resumen.append((n, "ERROR", 0, 0))
            continue
        print(f"  {len(cands)} anuncios en su sección de oposiciones")
        for c in cands[:60]:
            it = classify.detectar_it(classify.norm(c["titulo"]), "", cfg["palabras_extra"])[0]
            print(("  [IT] " if it else "       ") + c["titulo"][:140])
        fdb, res = FakeDB(), {"revisados": 0, "encontrados": 0}
        _, fallos = scan._procesar(cands, fdb, cfg, res)
        if fdb.g:
            print("  --- de informática:")
        for g in sorted(fdb.g, key=lambda x: -x["score"]):
            print(f"  {g['score']:3} {g['nivel']:11} {'/'.join(g['grupos']) or '?':6} {g['puesto'][:40]:40} "
                  f"{g['lugar'][:22]:22} {g['tipo']}")
        resumen.append((n, "OK", len(cands), len(fdb.g)))
        if fallos:
            print(f"  ({fallos} anuncios no se pudieron leer)")
    print("\n===== RESUMEN =====")
    for n, est, c, it in resumen:
        aviso = "  <-- 0 anuncios: o no hubo ese día o el lector falla" if est == "OK" and c == 0 else ""
        print(f"  {n.upper():6} {est:5} {c:4} anuncios  {it:3} de informática{aviso}")


def demo(db, cfg):
    hoy = dt.date.today()
    ejemplos = [
        ("BOC", "Bases de la convocatoria para la provisión en propiedad de una plaza de Técnico/a de Sistemas Informáticos, "
                "personal funcionario, Grupo A, Subgrupo A2, mediante oposición libre.",
         "El plazo de presentación de solicitudes será de veinte días naturales a contar desde la publicación del extracto en el Boletín Oficial del Estado.",
         "Ayuntamiento de Torrelavega", "cantabria"),
        ("BOE", "Resolución de 20 de octubre de 2026, de la Secretaría de Estado de Función Pública, por la que se convoca proceso selectivo "
                "para ingreso, por el sistema general de acceso libre, en el Cuerpo de Gestión de Sistemas e Informática de la Administración del Estado.",
         "El proceso selectivo se realizará mediante el sistema de oposición. El plazo de presentación de solicitudes será de veinte días hábiles.",
         "MINISTERIO PARA LA TRANSFORMACIÓN DIGITAL Y DE LA FUNCIÓN PÚBLICA", None),
        ("BOE", "Resolución de 15 de octubre de 2026, del Ayuntamiento de Gijón/Xixón (Asturias), referente a la convocatoria para proveer varias plazas.",
         "Una plaza de Técnico/a Auxiliar de Informática, grupo C, subgrupo C1, como personal funcionario de carrera, mediante concurso-oposición, turno libre. "
         "El plazo de presentación de solicitudes será de veinte días naturales.", "ADMINISTRACIÓN LOCAL", None),
        ("BOE", "Resolución de la Universidad de Burgos, por la que se convoca proceso selectivo para cubrir una plaza de Técnico Especialista en Informática como personal laboral fijo.",
         "El sistema de selección será el de concurso-oposición. Grupo III. El plazo de presentación de solicitudes será de veinte días hábiles.", "UNIVERSIDADES", None),
        ("BOE", "Resolución de la Universidad de Sevilla, por la que se aprueba la relación definitiva de admitidos y excluidos en las pruebas selectivas para ingreso en la Escala de Analistas de Sistemas.",
         "", "UNIVERSIDADES", None),
    ]
    ids = []
    for i, (fu, tit, txt, dep, zona) in enumerate(ejemplos):
        r = classify.clasificar(tit, txt, dep, fu, hoy, zona, (), cfg.get("pesos"), cfg.get("grupos"))
        ids.append(db.guardar({"uid": f"DEMO:{i}", "fuente": fu, "fecha_pub": hoy.isoformat(), "titulo": tit,
                               "departamento": dep, "url": "https://www.boe.es/", "url_pdf": None, **r}))
        print(f"{r['score']:3} {r['nivel']:11} {tit[:80]}")
    # una apuntada de ejemplo con documentos iniciales y novedades
    iid = db.crear_manual("Técnico de Informática y Administración Electrónica", "Ayuntamiento de Tarazona", ["A2"],
                          "Tarazona (Zaragoza)", 280, "resto", "https://tarazona.sedelectronica.es/")
    for t in ("Convocatoria proceso selectivo BOE-A-2026-20186", "Bases proceso selectivo bop_6324_2026", "ANEXO II",
              "DECRETO 2026-1589 Rectificación error material Bases Técnico Informática"):
        db.add_novedad(iid, "web", t, "https://tarazona.sedelectronica.es/#" + t, inicial=True)
    db.add_novedad(iid, "web", "Lista provisional de admitidos y excluidos", "https://tarazona.sedelectronica.es/#lista")
    db.add_novedad(iid, "BOE", "Fase del proceso: anuncio de fecha del primer ejercicio", "https://www.boe.es/#ej1")
    if ids and ids[1]:
        db.set_estado(ids[1], "apuntado")
    print("Ejemplos guardados (DEMO: y MANUAL:). Para empezar limpio borra la carpeta data/")


if __name__ == "__main__":
    main()
