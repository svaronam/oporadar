"""Vigila que cada fuente funcione y genera alertas (que la APK notifica) cuando algo huele mal:

- una fuente da error al leerse (web caída, cambio de dirección...);
- una fuente lleva 3 de los últimos 5 días laborables sin un solo anuncio de oposiciones, lo que en
  BOE/BOC/BOCYL/BOPA/BOPV casi nunca pasa y suele significar que su web ha cambiado de formato;
- hay anuncios que llevan más de 3 días sin poder leerse.
Cada alerta tiene una clave para no repetirse (una por fuente y día, o por semana en el caso de «vacía»).
"""
import datetime as dt
import logging

log = logging.getLogger("oporadar")
NOMBRES = {"BOE": "el BOE", "BOC": "el BOC (Cantabria)", "BOCYL": "el BOCYL (Castilla y León)",
           "BOPA": "el BOPA (Asturias)", "BOPV": "el BOPV (País Vasco)"}


def revisar(db, hoy=None):
    from .scan import FUENTES
    hoy = hoy or dt.date.today()
    nuevas = 0
    for f in FUENTES:
        esc = db.escaneos_fuente(f, (hoy - dt.timedelta(days=10)).isoformat())
        if not esc:
            continue
        nombre = NOMBRES.get(f, f)
        ult = esc[-1]
        err = ult.get("error") or ""
        if err and not err[0].isdigit():
            if db.add_alerta(f"{f}:error:{hoy.isoformat()}", f,
                             f"No consigo leer {nombre}: {err[:140]}. Lo reintentaré en la próxima barrida."):
                nuevas += 1
        laborables = [e for e in esc
                      if dt.date.fromisoformat(e["fecha"]).weekday() < 5
                      and (hoy - dt.date.fromisoformat(e["fecha"])).days >= 2 and e["ok"]][-5:]
        vacios = [e for e in laborables if not e["revisados"]]
        if len(laborables) >= 3 and len(vacios) >= 3:
            semana = hoy.isocalendar()
            if db.add_alerta(f"{f}:vacio:{semana[0]}-{semana[1]}", f,
                             f"{nombre[0].upper() + nombre[1:]} lleva {len(vacios)} días laborables sin anuncios de "
                             f"oposiciones. Probablemente ha cambiado su web: pásame data/debug/ para ajustarlo."):
                nuevas += 1
        for e in esc:
            if (e.get("error") or "").startswith(tuple("0123456789")) and \
                    (hoy - dt.date.fromisoformat(e["fecha"])).days >= 3:
                if db.add_alerta(f"{f}:sinleer:{e['fecha']}", f,
                                 f"Hay anuncios de {nombre} del {e['fecha']} que no consigo leer desde hace días. "
                                 f"Revisa ese boletín a mano por si acaso."):
                    nuevas += 1
    if nuevas:
        log.warning("%d alerta(s) de funcionamiento nuevas", nuevas)
    return nuevas
