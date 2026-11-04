import contextlib
import json
import sqlite3
import threading
import time

ESQUEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  uid TEXT UNIQUE NOT NULL,
  fuente TEXT, fecha_pub TEXT, titulo TEXT, organismo TEXT, departamento TEXT,
  url TEXT, url_pdf TEXT, detalle TEXT,
  zona TEXT, sistema TEXT, vinculo TEXT, acceso TEXT, grupos TEXT, grupo_inferido INTEGER,
  tipo TEXT, plazo_txt TEXT, plazo_fin TEXT,
  score INTEGER, nivel TEXT, desglose TEXT,
  estado TEXT DEFAULT 'nuevo',
  creado REAL
);
CREATE INDEX IF NOT EXISTS ix_items_score ON items(score);
CREATE INDEX IF NOT EXISTS ix_items_fecha ON items(fecha_pub);
CREATE TABLE IF NOT EXISTS escaneos (
  fuente TEXT, fecha TEXT, ok INTEGER, revisados INTEGER, encontrados INTEGER, error TEXT, ts REAL,
  PRIMARY KEY (fuente, fecha)
);
-- páginas que vigilas de una convocatoria a la que estás apuntado (sede electrónica, portal de empleo...)
CREATE TABLE IF NOT EXISTS vigilancias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL, url TEXT NOT NULL, nombre TEXT,
  creado REAL, ultimo_check REAL, ok INTEGER, n_docs INTEGER DEFAULT 0, error TEXT,
  UNIQUE(item_id, url)
);
CREATE TABLE IF NOT EXISTS docs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vig_id INTEGER NOT NULL, clave TEXT NOT NULL, texto TEXT, url TEXT, visto REAL,
  UNIQUE(vig_id, clave)
);
-- todo lo que va apareciendo en una convocatoria apuntada (documentos nuevos, anuncios en BOE/BOC...)
CREATE TABLE IF NOT EXISTS novedades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL, ts REAL, origen TEXT, titulo TEXT, url TEXT,
  inicial INTEGER DEFAULT 0, leida INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_nov ON novedades(item_id, url);
CREATE TABLE IF NOT EXISTS alertas (
  id INTEGER PRIMARY KEY AUTOINCREMENT, clave TEXT UNIQUE, fuente TEXT, texto TEXT, ts REAL
);
"""
COLS_NUEVAS = {"puesto": "TEXT", "lugar": "TEXT", "km": "INTEGER", "escala": "TEXT"}


class DB:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        with self._c() as c:
            c.executescript(ESQUEMA)
            tiene = {r["name"] for r in c.execute("PRAGMA table_info(items)")}
            for col, tipo in COLS_NUEVAS.items():  # migración desde la v1.0
                if col not in tiene:
                    c.execute(f"ALTER TABLE items ADD COLUMN {col} {tipo}")
            c.execute("UPDATE items SET estado='apuntado' WHERE estado='presentado'")

    @contextlib.contextmanager
    def _c(self):
        """Conexión que hace commit y se CIERRA al salir (el servicio corre meses en la Pi)."""
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    # ------------------------------------------------------------------ items
    COLS = ["uid", "fuente", "fecha_pub", "titulo", "organismo", "departamento", "url", "url_pdf", "detalle",
            "zona", "sistema", "vinculo", "acceso", "grupos", "grupo_inferido", "tipo", "plazo_txt", "plazo_fin",
            "score", "nivel", "desglose", "puesto", "lugar", "km", "escala"]

    def _row(self, it):
        row = dict(it)
        row["grupos"] = ",".join(it.get("grupos") or [])
        row["grupo_inferido"] = 1 if it.get("grupo_inferido") else 0
        row["desglose"] = json.dumps(it.get("desglose") or [], ensure_ascii=False)
        return [row.get(k) for k in self.COLS]

    def guardar(self, it: dict):
        """Inserta o actualiza (sin pisar el estado que hayas marcado). Devuelve el id si es nuevo, si no None."""
        vals = self._row(it)
        cols = self.COLS
        with self.lock, self._c() as c:
            ex = c.execute("SELECT id FROM items WHERE uid=?", (it["uid"],)).fetchone()
            if ex:
                sets = ",".join(f"{k}=?" for k in cols[1:])
                c.execute(f"UPDATE items SET {sets} WHERE uid=?", vals[1:] + [it["uid"]])
                return None
            cur = c.execute(f"INSERT OR IGNORE INTO items ({','.join(cols)},creado) VALUES ({','.join('?' * len(cols))},?)",
                            vals + [time.time()])
            return cur.lastrowid if cur.rowcount == 1 else None

    def actualizar_campos(self, item_id, **campos):
        if not campos:
            return
        if "grupos" in campos and isinstance(campos["grupos"], list):
            campos["grupos"] = ",".join(campos["grupos"])
        sets = ",".join(f"{k}=?" for k in campos)
        with self.lock, self._c() as c:
            c.execute(f"UPDATE items SET {sets} WHERE id=?", list(campos.values()) + [item_id])

    def sin_titular(self):
        with self._c() as c:
            return [self._fila(r) for r in c.execute("SELECT * FROM items WHERE puesto IS NULL")]

    def escaneado(self, fuente, fecha):
        with self._c() as c:
            r = c.execute("SELECT ok FROM escaneos WHERE fuente=? AND fecha=?", (fuente, fecha)).fetchone()
            return bool(r and r["ok"])

    def hubo_escaneo(self, fuente, fecha):
        with self._c() as c:
            return c.execute("SELECT 1 FROM escaneos WHERE fuente=? AND fecha=?", (fuente, fecha)).fetchone() is not None

    def escaneos_fuente(self, fuente, desde):
        with self._c() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM escaneos WHERE fuente=? AND fecha>=? ORDER BY fecha", (fuente, desde))]

    # ------------------------------------------------------------------ alertas de funcionamiento
    def add_alerta(self, clave, fuente, texto):
        with self.lock, self._c() as c:
            cur = c.execute("INSERT OR IGNORE INTO alertas (clave,fuente,texto,ts) VALUES (?,?,?,?)",
                            (clave, fuente, texto, time.time()))
            return cur.lastrowid if cur.rowcount else None

    def alertas_desde(self, aid, limite=20):
        with self._c() as c:
            return [dict(r) for r in c.execute("SELECT * FROM alertas WHERE id>? ORDER BY id LIMIT ?", (aid, limite))]

    def alertas_recientes(self, horas=72):
        with self._c() as c:
            return [dict(r) for r in c.execute("SELECT * FROM alertas WHERE ts>? ORDER BY id DESC",
                                               (time.time() - horas * 3600,))]

    def max_alerta(self):
        with self._c() as c:
            return c.execute("SELECT COALESCE(MAX(id),0) m FROM alertas").fetchone()["m"]

    def marcar_escaneo(self, fuente, fecha, ok, revisados=0, encontrados=0, error=None):
        with self.lock, self._c() as c:
            c.execute("INSERT OR REPLACE INTO escaneos VALUES (?,?,?,?,?,?,?)",
                      (fuente, fecha, 1 if ok else 0, revisados, encontrados, error, time.time()))

    def ultimos_escaneos(self, n=20):
        with self._c() as c:
            return [dict(r) for r in c.execute("SELECT * FROM escaneos ORDER BY ts DESC LIMIT ?", (n,))]

    @staticmethod
    def _fila(r):
        d = dict(r)
        d["grupos"] = [g for g in (d.get("grupos") or "").split(",") if g]
        d["desglose"] = json.loads(d.get("desglose") or "[]")
        return d

    def item(self, item_id):
        with self._c() as c:
            r = c.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
            return self._fila(r) if r else None

    def listar(self, nivel=None, tipo=None, q=None, estado=None, ocultar_descartadas=True, limite=300, desde_id=None):
        sql, args = "SELECT * FROM items WHERE fuente!='MANUAL'", []
        if nivel:
            ns = nivel.split(",")
            sql += f" AND nivel IN ({','.join('?' * len(ns))})"
            args += ns
        if tipo:
            ts = tipo.split(",")
            sql += f" AND tipo IN ({','.join('?' * len(ts))})"
            args += ts
        if estado:
            sql += " AND estado=?"
            args.append(estado)
        elif ocultar_descartadas:
            sql += " AND estado!='descartado'"
        if q:
            sql += " AND (titulo LIKE ? OR organismo LIKE ? OR detalle LIKE ? OR puesto LIKE ? OR lugar LIKE ?)"
            args += [f"%{q}%"] * 5
        if desde_id is not None:
            sql += " AND id>?"
            args.append(desde_id)
        sql += " ORDER BY id ASC LIMIT ?" if desde_id is not None else " ORDER BY fecha_pub DESC, score DESC LIMIT ?"
        args.append(limite)
        with self._c() as c:
            return [self._fila(r) for r in c.execute(sql, args)]

    def max_id(self):
        with self._c() as c:
            return c.execute("SELECT COALESCE(MAX(id),0) m FROM items").fetchone()["m"]

    def set_estado(self, item_id, estado):
        with self.lock, self._c() as c:
            c.execute("UPDATE items SET estado=? WHERE id=?", (estado, item_id))

    def contar(self):
        with self._c() as c:
            d = {r["nivel"]: r["n"] for r in c.execute(
                "SELECT nivel, COUNT(*) n FROM items WHERE estado!='descartado' AND fuente!='MANUAL' GROUP BY nivel")}
            d["_apuntadas"] = c.execute("SELECT COUNT(*) n FROM items WHERE estado='apuntado'").fetchone()["n"]
            d["_sin_leer"] = c.execute(
                "SELECT COUNT(*) n FROM novedades n JOIN items i ON i.id=n.item_id "
                "WHERE i.estado='apuntado' AND n.leida=0 AND n.inicial=0").fetchone()["n"]
            return d

    def crear_manual(self, puesto, organismo, grupos, lugar, km, zona, url, sistema=None, vinculo=None):
        uid = f"MANUAL:{time.time():.6f}"
        it = {"uid": uid, "fuente": "MANUAL", "fecha_pub": time.strftime("%Y-%m-%d"), "titulo": puesto,
              "organismo": organismo, "departamento": "", "url": url, "url_pdf": None, "detalle": "",
              "zona": zona, "sistema": sistema, "vinculo": vinculo, "acceso": "libre", "grupos": grupos,
              "grupo_inferido": False, "tipo": "convocatoria", "plazo_txt": "", "plazo_fin": None, "score": None,
              "nivel": "apuntada", "desglose": [], "puesto": puesto, "lugar": lugar, "km": km, "escala": ""}
        iid = self.guardar(it)
        self.set_estado(iid, "apuntado")
        return iid

    def apuntadas(self):
        with self._c() as c:
            items = [self._fila(r) for r in c.execute(
                "SELECT * FROM items WHERE estado='apuntado' ORDER BY creado DESC")]
            for it in items:
                it["novedades"] = [dict(r) for r in c.execute(
                    "SELECT * FROM novedades WHERE item_id=? ORDER BY inicial ASC, ts DESC, id DESC", (it["id"],))]
                it["vigilancias"] = [dict(r) for r in c.execute(
                    "SELECT * FROM vigilancias WHERE item_id=? ORDER BY id", (it["id"],))]
                it["sin_leer"] = sum(1 for n in it["novedades"] if not n["leida"] and not n["inicial"])
            items.sort(key=lambda x: (-x["sin_leer"], -(max([n["ts"] for n in x["novedades"]] or [x["creado"] or 0]))))
            return items

    # ------------------------------------------------------------------ vigilancias de páginas
    def add_vigilancia(self, item_id, url, nombre=""):
        with self.lock, self._c() as c:
            cur = c.execute("INSERT OR IGNORE INTO vigilancias (item_id,url,nombre,creado) VALUES (?,?,?,?)",
                            (item_id, url, nombre, time.time()))
            if cur.rowcount:
                return cur.lastrowid
            return c.execute("SELECT id FROM vigilancias WHERE item_id=? AND url=?", (item_id, url)).fetchone()["id"]

    def vigilancias(self, solo_apuntadas=True):
        sql = "SELECT v.* FROM vigilancias v JOIN items i ON i.id=v.item_id"
        if solo_apuntadas:
            sql += " WHERE i.estado='apuntado'"
        with self._c() as c:
            return [dict(r) for r in c.execute(sql)]

    def vigilancia(self, vid):
        with self._c() as c:
            r = c.execute("SELECT * FROM vigilancias WHERE id=?", (vid,)).fetchone()
            return dict(r) if r else None

    def del_vigilancia(self, vid):
        with self.lock, self._c() as c:
            c.execute("DELETE FROM docs WHERE vig_id=?", (vid,))
            c.execute("DELETE FROM vigilancias WHERE id=?", (vid,))

    def claves_docs(self, vid):
        with self._c() as c:
            return {r["clave"] for r in c.execute("SELECT clave FROM docs WHERE vig_id=?", (vid,))}

    def add_doc(self, vid, clave, texto, url):
        with self.lock, self._c() as c:
            c.execute("INSERT OR IGNORE INTO docs (vig_id,clave,texto,url,visto) VALUES (?,?,?,?,?)",
                      (vid, clave, texto, url, time.time()))

    def fin_vigilancia(self, vid, ok, n_docs, error=None):
        with self.lock, self._c() as c:
            c.execute("UPDATE vigilancias SET ultimo_check=?, ok=?, n_docs=?, error=? WHERE id=?",
                      (time.time(), 1 if ok else 0, n_docs, error, vid))

    # ------------------------------------------------------------------ novedades
    def add_novedad(self, item_id, origen, titulo, url, inicial=False):
        with self.lock, self._c() as c:
            cur = c.execute("INSERT OR IGNORE INTO novedades (item_id,ts,origen,titulo,url,inicial,leida) "
                            "VALUES (?,?,?,?,?,?,?)",
                            (item_id, time.time(), origen, titulo, url, 1 if inicial else 0, 1 if inicial else 0))
            return cur.lastrowid if cur.rowcount else None

    def novedades_desde(self, nid, limite=50):
        with self._c() as c:
            return [dict(r) for r in c.execute(
                "SELECT n.*, i.puesto, i.lugar, i.organismo, i.grupos FROM novedades n JOIN items i ON i.id=n.item_id "
                "WHERE n.id>? AND n.inicial=0 AND i.estado='apuntado' ORDER BY n.id ASC LIMIT ?", (nid, limite))]

    def max_nov(self):
        with self._c() as c:
            return c.execute("SELECT COALESCE(MAX(id),0) m FROM novedades").fetchone()["m"]

    def marcar_leidas(self, item_id):
        with self.lock, self._c() as c:
            c.execute("UPDATE novedades SET leida=1 WHERE item_id=?", (item_id,))

    def borrar_novedad(self, nid):
        with self.lock, self._c() as c:
            c.execute("DELETE FROM novedades WHERE id=?", (nid,))
