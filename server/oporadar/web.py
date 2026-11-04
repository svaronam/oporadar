"""Servidor HTTP (sin dependencias): web para el móvil + API que consulta la APK para las notificaciones."""
import datetime as dt
import json
import logging
import os
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import geo, scan, vigilar

log = logging.getLogger("oporadar")
STATIC = os.path.join(os.path.dirname(__file__), "static")
ESTADOS = {"nuevo", "visto", "favorito", "descartado", "apuntado"}
VERSION = "1.2.0"


def make_handler(db, cfg):
    class H(BaseHTTPRequestHandler):
        server_version = "OpoRadar/" + VERSION

        def log_message(self, fmt, *a):
            log.debug("%s %s", self.address_string(), fmt % a)

        # ---------------------------------------------------- helpers
        def _json(self, obj, code=200):
            b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def _auth(self, qs):
            tok = cfg.get("token") or ""
            if not tok:
                return True
            dado = self.headers.get("X-Token") or (qs.get("token") or [""])[0]
            if dado == tok:
                return True
            self._json({"error": "token incorrecto"}, 401)
            return False

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode("utf-8"))
            except Exception:
                return {}

        # ---------------------------------------------------- GET
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)
            q1 = lambda k, d=None: (qs.get(k) or [d])[0]  # noqa: E731
            if u.path in ("/", "/index.html"):
                with open(os.path.join(STATIC, "index.html"), "rb") as f:
                    b = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(b)
                return
            if not u.path.startswith("/api/"):
                return self._json({"error": "no encontrado"}, 404)
            if not self._auth(qs):
                return
            if u.path == "/api/items":
                items = db.listar(nivel=q1("nivel"), tipo=q1("tipo"), q=q1("q"), estado=q1("estado"),
                                  ocultar_descartadas=q1("descartadas") != "1", limite=int(q1("limite", 400)))
                return self._json({"items": items})
            if u.path == "/api/apuntadas":
                return self._json({"items": db.apuntadas()})
            if u.path == "/api/nuevas":
                # La APK guarda el último id de anuncio y de novedad que ha visto y pregunta por los posteriores
                desde = int(q1("desde", "0"))
                desde_nov = int(q1("desde_nov", "-1"))
                desde_al = int(q1("desde_alerta", "-1"))
                maxid, maxnov = db.max_id(), db.max_nov()
                res = {"items": [], "max_id": maxid, "novedades": [], "max_nov": maxnov,
                       "alertas": [], "max_alerta": db.max_alerta()}
                if desde_al >= 0:
                    res["alertas"] = db.alertas_desde(desde_al)
                if desde >= 0:
                    n = cfg["notificar"]
                    items = db.listar(nivel=",".join(n["niveles"]), tipo=",".join(n["tipos"]), desde_id=desde, limite=50)
                    res["items"] = sorted(items, key=lambda x: x["id"])
                if desde_nov >= 0:
                    res["novedades"] = db.novedades_desde(desde_nov)
                return self._json(res)
            if u.path == "/api/estado":
                return self._json({
                    "version": VERSION, "barrida": scan.estado, "escaneos": db.ultimos_escaneos(12),
                    "contadores": db.contar(), "hora_barrida": cfg.get("hora_barrida", "09:20"),
                    "vigilar_cada_horas": cfg.get("vigilar_cada_horas", 4),
                    "alertas": db.alertas_recientes(72),
                    "fuentes": [k.upper() for k, v in (cfg.get("fuentes") or {}).items() if v],
                    "grupos": cfg["grupos"], "ahora": time.time()})
            return self._json({"error": "no encontrado"}, 404)

        # ---------------------------------------------------- POST
        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)
            if not self._auth(qs):
                return
            b = self._body()
            parts = u.path.strip("/").split("/")

            if u.path == "/api/barrida":
                dias = int(b.get("dias") or 0) or None
                if scan.estado["en_curso"]:
                    return self._json({"ok": False, "mensaje": "Ya hay una barrida en curso"})
                threading.Thread(target=scan.barrida, args=(db, cfg, dias, bool(b.get("forzar"))), daemon=True).start()
                return self._json({"ok": True, "mensaje": "Barrida lanzada"})

            if u.path == "/api/manual":
                # apuntarte a algo que el radar no encontró (o anterior a instalarlo)
                puesto = (b.get("puesto") or "").strip()
                organismo = (b.get("organismo") or "").strip()
                if not puesto or not organismo:
                    return self._json({"error": "Pon al menos el puesto y el organismo"}, 400)
                grupos = [g.strip().upper() for g in (b.get("grupo") or "").replace(",", "/").split("/") if g.strip()]
                from .classify import detectar_zona
                from .util import norm
                zona = detectar_zona(norm(organismo), "", "", None)
                lugar, km = geo.lugar_y_km(organismo, "", zona)
                url = (b.get("url") or "").strip()
                iid = db.crear_manual(puesto, organismo, grupos, lugar, km, zona, url,
                                      b.get("sistema") or None, b.get("vinculo") or None)
                if url:
                    vid = db.add_vigilancia(iid, url)
                    vigilar.revisar(db, db.vigilancia(vid), cfg["data_dir"])
                return self._json({"ok": True, "id": iid})

            if len(parts) == 4 and parts[:2] == ["api", "items"]:
                iid = int(parts[2])
                if parts[3] == "estado":
                    est = b.get("estado")
                    if est not in ESTADOS:
                        return self._json({"error": "estado no válido"}, 400)
                    db.set_estado(iid, est)
                    if est == "apuntado":
                        it = db.item(iid)
                        if it and it["fuente"] != "MANUAL":
                            # el propio anuncio es el primer documento de la ficha
                            db.add_novedad(iid, it["fuente"], f"{it['fuente']}: {it['titulo']}",
                                           it.get("url_pdf") or it["url"], inicial=True)
                    return self._json({"ok": True})
                if parts[3] == "vigilar":
                    url = (b.get("url") or "").strip()
                    if not url.startswith("http"):
                        return self._json({"error": "Pega una URL que empiece por http"}, 400)
                    vid = db.add_vigilancia(iid, url, (b.get("nombre") or "").strip())
                    vigilar.revisar(db, db.vigilancia(vid), cfg["data_dir"])
                    return self._json({"ok": True, "vigilancia": db.vigilancia(vid)})
                if parts[3] == "leido":
                    db.marcar_leidas(iid)
                    return self._json({"ok": True})
                if parts[3] == "editar":
                    campos = {k: b[k] for k in ("puesto", "lugar", "organismo", "plazo_txt") if k in b}
                    if "grupo" in b:
                        campos["grupos"] = [g.strip().upper() for g in b["grupo"].replace(",", "/").split("/") if g.strip()]
                    db.actualizar_campos(iid, **campos)
                    return self._json({"ok": True})

            if len(parts) == 4 and parts[:2] == ["api", "vigilancias"]:
                vid = int(parts[2])
                if parts[3] == "revisar":
                    v = db.vigilancia(vid)
                    if not v:
                        return self._json({"error": "no existe"}, 404)
                    n = vigilar.revisar(db, v, cfg["data_dir"])
                    return self._json({"ok": True, "nuevos": n, "vigilancia": db.vigilancia(vid)})
                if parts[3] == "borrar":
                    db.del_vigilancia(vid)
                    return self._json({"ok": True})

            if len(parts) == 4 and parts[:2] == ["api", "novedades"] and parts[3] == "borrar":
                db.borrar_novedad(int(parts[2]))
                return self._json({"ok": True})

            return self._json({"error": "no encontrado"}, 404)

    return H


def programador(db, cfg):
    """Barrida de boletines una vez al día a 'hora_barrida' (y al arrancar si hoy aún no se ha hecho)
    y revisión de las páginas vigiladas de tus convocatorias cada 'vigilar_cada_horas'."""
    hh, mm = [int(x) for x in cfg.get("hora_barrida", "09:20").split(":")]
    cada = float(cfg.get("vigilar_cada_horas", 4)) * 3600
    ultimo, ultima_vig = None, 0
    time.sleep(20)  # deja que la red (WiFi/Tailscale) se levante tras un reinicio
    while True:
        ahora = dt.datetime.now()
        hoy = ahora.date()
        if ultimo != hoy and (ahora.hour, ahora.minute) >= (hh, mm):
            log.info("Barrida diaria programada")
            scan.barrida(db, cfg)
            ultimo = hoy
        if time.time() - ultima_vig >= cada and 7 <= ahora.hour <= 23:
            n = vigilar.revisar_todas(db, cfg["data_dir"])
            log.info("Páginas vigiladas revisadas: %d documentos nuevos", n)
            ultima_vig = time.time()
        time.sleep(60)


def servir(db, cfg):
    try:
        scan.rellenar_titulares(db, cfg)
    except Exception as e:
        log.warning("No se pudieron completar titulares antiguos: %s", e)
    threading.Thread(target=programador, args=(db, cfg), daemon=True).start()
    srv = ThreadingHTTPServer((cfg["host"], int(cfg["puerto"])), make_handler(db, cfg))
    log.info("OpoRadar %s escuchando en http://%s:%s", VERSION, cfg["host"], cfg["puerto"])
    srv.serve_forever()
