"""La barrida diaria: recorre las fuentes, filtra lo de informática, puntúa y guarda."""
import datetime as dt
import logging
import threading
import time
import traceback

from . import classify, salud, vigilar
from .sources import boc, bocyl, boe, bopa, bopv, rss
from .util import norm

log = logging.getLogger("oporadar")
_lock = threading.Lock()
estado = {"en_curso": False, "inicio": None, "fin": None, "mensaje": "", "nuevos": 0}


FUENTES = ["BOE", "BOC", "BOCYL", "BOPA", "BOPV"]
VENTANA_REINTENTO = 14  # días hacia atrás en los que se reintenta lo que falló o aún no estaba publicado


def _procesar(cands, db, cfg, resumen):
    """Clasifica y guarda. Devuelve (nuevos, fallos_de_lectura)."""
    pausa = cfg.get("pausa_entre_peticiones", 0.4)
    extra = cfg.get("palabras_extra") or []
    nuevos = fallos = 0
    for c in cands:
        resumen["revisados"] += 1
        tn = norm(c["titulo"])
        es_it_titulo = classify.detectar_it(tn, "", extra)[0]
        tipo_titulo = classify.detectar_tipo(tn)
        texto = c.get("texto_inicial", "")
        # Leemos el texto completo si el título ya es de informática (para sacar grupo, sistema, plazo...)
        # o si es una convocatoria/OEP con título genérico ("...para proveer varias plazas").
        if es_it_titulo or tipo_titulo in ("convocatoria", "oep"):
            try:
                texto = c["get_texto"]() or texto
            except Exception as e:  # un anuncio que falla no tumba la barrida: el día se reintentará
                fallos += 1
                log.warning("No se pudo leer %s: %s", c["url"], e)
            time.sleep(pausa)
        r = classify.clasificar(c["titulo"], texto, c.get("departamento", ""), c["fuente"], c["fecha_pub"],
                                c.get("fuente_zona"), extra, cfg.get("pesos"), cfg.get("grupos"),
                                zona_defecto=c.get("zona_defecto"))
        if not r:
            continue
        item = {
            "uid": c["uid"], "fuente": c["fuente"], "fecha_pub": c["fecha_pub"].isoformat(),
            "titulo": c["titulo"], "departamento": c.get("departamento", ""), "url": c["url"],
            "url_pdf": c.get("url_pdf"), **r,
        }
        if db.guardar(item):
            nuevos += 1
            log.info("NUEVA [%s %s] %s", item["score"], item["nivel"], item["titulo"][:110])
            try:
                vigilar.enlazar_con_apuntadas(db, item)
            except Exception as e:  # pragma: no cover
                log.warning("No se pudo enlazar con apuntadas: %s", e)
        resumen["encontrados"] += 1
    return nuevos, fallos


def _obtener(nombre, cfg):
    if nombre == "BOE":
        return boe.candidatos
    if nombre == "BOC":
        return lambda f: boc.candidatos(f, cfg["data_dir"], cfg.get("boc_url_plantilla") or None)
    if nombre == "BOCYL":
        return bocyl.candidatos
    if nombre == "BOPA":
        return bopa.candidatos
    return None


def fechas_a_revisar(db, fuente, dias, forzar, hoy):
    """Los últimos `dias` días que aún no estén bien revisados + los de la ventana de reintento que fallaron."""
    pendientes = []
    for i in range(max(dias, VENTANA_REINTENTO) - 1, -1, -1):
        f = hoy - dt.timedelta(days=i)
        if forzar and i < dias:
            pendientes.append(f)
        elif not db.escaneado(fuente, f.isoformat()) and (i < dias or db.hubo_escaneo(fuente, f.isoformat())):
            pendientes.append(f)
    return pendientes


def barrida(db, cfg, dias=None, forzar=False):
    """Revisa todas las fuentes activas. Devuelve nº de anuncios nuevos (-1 si ya había una en curso)."""
    if not _lock.acquire(blocking=False):
        return -1
    try:
        estado.update(en_curso=True, inicio=time.time(), mensaje="Barrida en curso", nuevos=0)
        hoy = dt.date.today()
        dias = dias or cfg.get("dias_atras", 4)
        total = 0
        activas = cfg.get("fuentes") or {}
        for nombre in FUENTES:
            if not activas.get(nombre.lower(), True):
                continue
            fechas = fechas_a_revisar(db, nombre, dias, forzar, hoy)
            if not fechas:
                continue
            if nombre == "BOPV":
                total += _bopv(fechas, db, cfg, hoy)
                continue
            obtener = _obtener(nombre, cfg)
            for f in fechas:
                total += _una(nombre, f, lambda f=f: obtener(f), db, cfg, hoy)
        for fuente in cfg.get("rss") or []:
            desde = hoy - dt.timedelta(days=dias)
            total += _una(fuente["nombre"], hoy, lambda fu=fuente: rss.candidatos(fu, desde), db, cfg, hoy)
        try:
            salud.revisar(db, hoy)
        except Exception as e:  # pragma: no cover
            log.warning("Revisión de salud fallida: %s", e)
        estado.update(mensaje=f"Barrida terminada: {total} nuevas", nuevos=total)
        return total
    finally:
        estado.update(en_curso=False, fin=time.time())
        _lock.release()


def _marcar(db, nombre, fecha, hoy, cands, resumen, fallos, error=None):
    if error:
        db.marcar_escaneo(nombre, fecha.isoformat(), False, resumen["revisados"], resumen["encontrados"], error[:300])
    elif fallos:
        db.marcar_escaneo(nombre, fecha.isoformat(), False, resumen["revisados"], resumen["encontrados"],
                          f"{fallos} anuncio(s) no se pudieron leer; se reintentará")
    elif not cands and (hoy - fecha).days <= 1:
        # puede que el boletín de hoy/ayer aún no esté publicado: no lo damos por revisado
        db.marcar_escaneo(nombre, fecha.isoformat(), False, 0, 0, None)
    else:
        db.marcar_escaneo(nombre, fecha.isoformat(), True, resumen["revisados"], resumen["encontrados"], None)


def _una(nombre, fecha, obtener, db, cfg, hoy=None):
    hoy = hoy or dt.date.today()
    resumen = {"revisados": 0, "encontrados": 0}
    try:
        estado["mensaje"] = f"Leyendo {nombre} {fecha.isoformat()}"
        cands = obtener()
        n, fallos = _procesar(cands, db, cfg, resumen)
        _marcar(db, nombre, fecha, hoy, cands, resumen, fallos)
        log.info("%s %s: %d revisados, %d de informática, %d nuevos%s", nombre, fecha, resumen["revisados"],
                 resumen["encontrados"], n, f", {fallos} sin leer" if fallos else "")
        return n
    except Exception as e:
        log.error("%s %s falló: %s\n%s", nombre, fecha, e, traceback.format_exc())
        _marcar(db, nombre, fecha, hoy, [], resumen, 0, f"{type(e).__name__}: {e}")
        return 0


def _bopv(fechas, db, cfg, hoy):
    """El BOPV se recorre por número de boletín: una pasada cubre todo el rango."""
    try:
        estado["mensaje"] = "Leyendo BOPV"
        por_fecha = bopv.candidatos_por_fecha(min(fechas))
    except Exception as e:
        log.error("BOPV falló: %s", e)
        for f in fechas:
            db.marcar_escaneo("BOPV", f.isoformat(), False, 0, 0, f"{type(e).__name__}: {e}"[:300])
        return 0
    total = 0
    for f in fechas:
        cands = por_fecha.get(f, [])
        total += _una("BOPV", f, lambda c=cands: c, db, cfg, hoy)
    return total


def rellenar_titulares(db, cfg):
    """Migración: calcula puesto/lugar/km/escala de los anuncios guardados con una versión anterior."""
    n = 0
    for it in db.sin_titular():
        if it["fuente"] == "MANUAL":
            continue
        r = classify.clasificar(it["titulo"], it.get("detalle") or "", it.get("departamento") or "", it["fuente"],
                                None, it["zona"] if it["fuente"] != "BOE" else None,
                                cfg.get("palabras_extra") or [], cfg.get("pesos"), cfg.get("grupos"))
        campos = {"puesto": "", "lugar": "", "km": None, "escala": ""}
        if r:
            campos = {"puesto": r["puesto"], "lugar": r["lugar"], "km": r["km"], "escala": r["escala"]}
            if not it["grupos"] and r["grupos"]:
                campos.update(grupos=r["grupos"], grupo_inferido=1 if r["grupo_inferido"] else 0)
        db.actualizar_campos(it["id"], **campos)
        n += 1
    if n:
        log.info("Titulares calculados para %d anuncios antiguos", n)
