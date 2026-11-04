"""Clasificador: ¿es de informática?, grupo, sistema selectivo, vínculo, zona, plazo... y la puntuación 0-100.

Todo trabaja sobre texto normalizado (minúsculas y sin tildes) para que los patrones sean simples.
"""
import datetime as dt
import re

from .geo import lugar_y_km
from .util import norm

# ---------------------------------------------------------------- informática
# Frases que contienen "informático" pero NO hablan de la plaza (medios para presentar la solicitud, etc.)
RUIDO_IT = [
    r"medios? informatic\w*", r"aplicacion(es)? informatic\w*", r"(en|por|y|o|mediante) soporte informatic\w*",
    # "plaza de Grupo Técnico..., con destino a la Unidad de ... Sistemas de Información": el destino no es el puesto
    r"(con )?destin\w* (en|a) (el |la |los |las )?(unidad?|servicio|area|seccion|departamento|direccion|subdireccion|"
    r"centro|gerencia|oficina)[^.;:]{0,110}",
    r"sistemas de informacion (clinic|asistencial|del laboratorio|sanitari|hospitalari|de personal|geografic)\w*",
    r"historia clinica electronica", r"sistemas de gestion de (la )?calidad",
    r"sede electronica", r"registro electronico", r"tramitacion electronica", r"notificaciones? electronica\w*",
    r"programas? informatic\w*", r"herramientas? informatic\w*", r"registro informatic\w*",
    r"procedimientos? informatic\w*", r"tratamiento informatic\w*", r"fichero informatic\w*",
    r"equipos? informatic\w*", r"plataforma informatic\w*", r"sistema informatico de (gestion|registro)",
    r"formato informatic\w*", r"via informatic\w*", r"aplicativo informatic\w*",
    r"ofimatica", r"conocimientos? de informatic\w*", r"informatica de usuario",
]
# Términos fuertes: si están en el título, es de informática
IT_FUERTE = [
    r"informatic\w*", r"tecnologias? de la informacion", r"sistemas de (la )?informacion",
    r"\btic\b", r"\bt\.i\.c\.", r"ciberseguridad", r"seguridad de la informacion",
    r"programador\w*", r"desarrollador\w*", r"analistas? (programador|de sistemas|de aplicaciones|funcional)",
    r"administrador\w* de (sistemas|redes|bases de datos)", r"microinformatica",
    r"tecnic\w*(/a)?\W+(\w+\W+){0,3}?(de |en )?sistemas\b(?! de (riego|depuracion|alarma|climatizacion))",
    r"sistemas y tecnologias", r"gestion de sistemas", r"ingenier\w*(/a)? (en |de )?(sistemas|software)",
    r"sistemas y redes", r"redes y sistemas", r"\bsistemas microinformaticos",
    # ampliación v1.2
    r"analistas?\b(?!\W+(clinic|quimic|de laboratorio|de riesgos|economic|financier|juridic|de credito|de mercado))",
    r"tecnic\w*(/a)?\W+(\w+\W+){0,4}?administracion (electronica|digital)", r"administracion electronica y (tic|sistemas)",
    r"desarroll\w* (de )?(software|aplicaciones|sistemas)", r"telecomunicaci\w*",
    r"ingenier\w*(/a)? (\w+ )?(de |en )?(telecomunicaci\w*|informatic\w*|datos|computadores|computacion|software)",
    r"transformacion digital", r"(cientific|analist|ingenier)\w*(/a)? de datos", r"big data", r"inteligencia artificial",
    r"\bredes (y comunicaciones|informaticas|de datos|y telecomunicaciones)", r"tecnic\w*(/a)?\W+(\w+\W+){0,3}?redes\b",
    r"seguridad informatica", r"\bcpd\b", r"soporte (tecnico informatico|informatico|microinformatico|a usuarios)",
    r"operador\w*(/a)? (de )?(ordenador|consola|sistemas)", r"\bdigitalizacion\b", r"\bstic\b", r"\bdevops\b",
    r"administrador\w*(/a)? (de )?(aplicaciones|plataformas|redes)", r"arquitect\w* (de )?(software|sistemas|soluciones)",
]
# En el cuerpo del anuncio exigimos que el término vaya pegado a una plaza / cuerpo / categoría
IT_ROL = re.compile(
    r"(plazas?|cuerpos?|escalas?|subescalas?|categorias?|puestos?|especialidad(es)?|clase|tecnic\w*(/a)?|"
    r"auxiliar\w*(/a)?|gestor\w*|operador\w*(/a)?|ingenier\w*(/a)?|titulad\w*(/a)?|responsable)"
    r"\W+(\w+\W+){0,6}?"
    r"(informatic\w*|tecnologias? de la informacion|sistemas (de informacion|informaticos|y tecnologias)|"
    r"\btic\b|ciberseguridad|microinformatica|sistemas y redes|redes y sistemas|administracion electronica|"
    r"telecomunicaci\w*|desarrollo de (software|aplicaciones)|transformacion digital|redes informaticas|sistemas\b)")
IT_FUERTE_RE = re.compile("|".join(IT_FUERTE))
RUIDO_RE = re.compile("|".join(RUIDO_IT))


def _limpiar_ruido(t):
    return RUIDO_RE.sub(" _ ", t)


NO_IT_TITULO = re.compile(r"cuerpos docentes universitarios|profesor\w* (titular|contratad\w*|ayudante|asociad\w*|permanente|"
                          r"colaborador|visitante)|catedratic|personal docente e investigador|\bpdi\b|plazas? de profesorado|"
                          r"investigador\w* (distinguid|postdoctoral|predoctoral)|ayudantes? doctor")


def detectar_it(titulo_n, texto_n, extra_kw=()):
    """Devuelve (es_it, posicion_en_texto, fragmento). posicion=-1 si sólo está en el título."""
    if NO_IT_TITULO.search(titulo_n):  # profesorado universitario: otra carrera, no es una oposición técnica
        return False, None, ""
    t = _limpiar_ruido(titulo_n)
    for kw in extra_kw:
        if kw and norm(kw) in t:
            return True, -1, titulo_n
    m = IT_FUERTE_RE.search(t)
    if m:
        pos = -1
        x = _limpiar_ruido(texto_n)
        m2 = IT_ROL.search(x) or IT_FUERTE_RE.search(x)
        if m2:
            pos = m2.start()
        return True, pos, titulo_n
    x = _limpiar_ruido(texto_n)
    for kw in extra_kw:
        if kw and norm(kw) in x:
            p = x.find(norm(kw))
            return True, p, _fragmento(texto_n, p)
    m = IT_ROL.search(x)
    if m:
        # 'sistemas' a secas sólo vale si va con 'tecnico' (evita "plazas ... sistema de oposicion")
        if m.group(m.lastindex) == "sistemas" and not re.match(r"tecnic", m.group(1)):
            m = None
            for mm in IT_ROL.finditer(x):
                if mm.group(mm.lastindex) != "sistemas" or re.match(r"tecnic", mm.group(1)):
                    m = mm
                    break
        if m:
            return True, m.start(), _fragmento(texto_n, m.start())
    return False, None, ""


def _fragmento(t, pos, ancho=220):
    if pos is None or pos < 0:
        return ""
    a = max(0, pos - 60)
    return t[a:pos + ancho].strip()


# ---------------------------------------------------------------- utilidades de "lo más cercano"
def _mas_cercano(texto, patrones, ancla):
    """patrones: {etiqueta: regex}. Devuelve la etiqueta cuyo match está más cerca de 'ancla'."""
    mejor, dist = None, 10 ** 9
    for etq, rx in patrones.items():
        for m in re.finditer(rx, texto):
            d = m.start() if ancla is None or ancla < 0 else abs(m.start() - ancla)
            if d < dist:
                mejor, dist = etq, d
            if ancla is None or ancla < 0:
                break  # sin ancla: gana la primera aparición
    return mejor


# ---------------------------------------------------------------- tipo de anuncio
TIPOS = [  # el orden importa
    ("correccion", r"correccion de error|se corrigen? error|rectifica|modifica\w* (de )?(las )?bases|se modifica la (resolucion|orden|convocatoria)"),
    ("seguimiento", r"admitid|excluid|aprobad[oa]s|nombra|tribunal|organo de seleccion|calificador|"
                    r"fecha\W.{0,40}(examen|ejercicio|prueba)|lugar\W.{0,40}celebracion|toma de posesion|adjudica|"
                    r"relacion (definitiva|provisional)|lista (definitiva|provisional)|resultados?|calificaciones|"
                    r"declara desiert|propuesta de (nombramiento|contratacion)|plantilla correctora|cese"),
    ("provision", r"libre designacion|concurso de traslados|concurso especifico|provision de puestos|"
                  r"comision de servicios|movilidad (inter|horizontal)"),
    ("oep", r"oferta de empleo publico|oferta publica de empleo|oferta de empleo"),
    ("convocatoria", r"convoca|convocatoria|\bbases\b|proveer|proceso selectivo|pruebas selectivas|"
                     r"bolsa de (empleo|trabajo)|provision\w* (en propiedad|de \w+ plazas?|de plazas?)|cubrir"),
]


def detectar_tipo(titulo_n, texto_n=""):
    for etq, rx in TIPOS:
        if re.search(rx, titulo_n):
            return etq
    cabeza = texto_n[:400]
    for etq, rx in TIPOS:
        if re.search(rx, cabeza):
            return etq
    return "otro"


# ---------------------------------------------------------------- sistema selectivo
def detectar_sistema(t, ancla):
    t2 = re.sub(r"concurso\W{0,3}oposicion\w*", " CONCOPO ", t)
    t2 = re.sub(r"fase de oposicion", " _ ", t2)
    pats = {
        "concurso-oposicion": r"CONCOPO",
        "oposicion": r"(mediante|sistema( selectivo)? de|por( el sistema de)?|procedimiento de|turno libre\W{1,3}|forma de|a traves de)\W{1,3}oposicion\b|\boposicion libre\b",
        "concurso": r"(mediante|sistema( selectivo)? de|por( el sistema de)?|procedimiento de|forma de)\W{1,3}concurso\b(?! (de traslados|especifico))|concurso de meritos|concurso excepcional|estabilizacion.{0,40}\bconcurso\b",
    }
    return _mas_cercano(t2, pats, ancla)


# ---------------------------------------------------------------- vínculo
def detectar_vinculo(t, ancla):
    pats = {
        "temporal": r"interin\w*|bolsa de (empleo|trabajo|interinos)|laboral temporal|caracter temporal|"
                    r"acumulacion de tareas|lista de espera|nombramiento provisional",
        "laboral": r"laboral fij\w*|personal laboral(?! temporal)|contrat\w* laboral indefinid\w*|"
                   r"plantilla de personal laboral|laboral indefinid\w*",
        "funcionario": r"funcionari\w* de carrera|personal funcionario|plantilla de (personal )?funcionari\w*|"
                       r"escala de administracion|\bsubescala\b|\bcuerpo (de|superior|tecnico|general|especial|auxiliar)|"
                       r"ingreso en (el|la) (cuerpo|escala)|como funcionari",
    }
    return _mas_cercano(t, pats, ancla)


# ---------------------------------------------------------------- acceso
def detectar_acceso(t):
    interna = bool(re.search(r"promocion interna", t))
    libre = bool(re.search(r"turno libre|acceso libre|ingreso libre|turno de acceso libre|sistema general de acceso libre|\blibre\b", t))
    if interna and not libre:
        return "interna"
    if libre:
        return "libre"
    return "desconocido"


# ---------------------------------------------------------------- grupo
GRUPO_RX = re.compile(r"(?:sub)?grupo\s*(?:de clasificacion\s*)?(?:profesional\s*)?[:\-]?\s*\(?\s*(a1|a2|c1|c2|a|b|c|e)\b")
PAREN_RX = re.compile(r"\((a1|a2|c1|c2)\)")
INFER = [
    ("A1", r"subescala tecnica,? (y )?clase superior|clase superior|" r"superior de sistemas|cuerpo superior|cuerpo tecnico superior|tecnicos? superior(es)? de (informatica|sistemas)|escala tecnica superior|tecnico de administracion especial.{0,30}superior"),
    ("B", r"grupo b\b|tecnico superior en (administracion de sistemas|desarrollo de aplicaciones|sistemas)"),
    ("A2", r"subescala tecnica,? (y )?clase media|clase media|gestion de sistemas e informatica|tecnic\w* (de grado )?medio|tecnico de gestion|gestion informatica|ingenier\w* tecnic|diplomad"),
    ("C1", r"tecnicos? auxiliar(es)? de informatica|tecnic\w* auxiliar|tecnic\w* especialista|programador|operador\w* (de )?(ordenador|informatic)|bachiller"),
]


def detectar_grupo(t, ancla):
    """Devuelve (lista de grupos detectados, inferido:bool). 'A' sin subgrupo => A1/A2."""
    hallados = []
    for rx in (GRUPO_RX, PAREN_RX):
        for m in rx.finditer(t):
            hallados.append((m.start(), m.group(1).upper()))
    if hallados:
        # nos quedamos con los más cercanos a la plaza de informática (puede haber varias plazas en un anuncio)
        if ancla is not None and ancla >= 0:
            # tramo de la plaza: desde la mención de informática hasta que empieza la descripción de otra plaza
            sig = re.search(r"(\.|;)?\s(una|dos|tres|cuatro|cinco|\d+) plazas? de|\n|\.\s+[a-z]\w+ plazas?|\. (subgrupo|grupo) ",
                            t[ancla + 25:])
            fin = ancla + 25 + sig.start() if sig else ancla + 400
            tramo = [(p, g) for p, g in hallados if ancla - 40 <= p <= fin]
            if tramo:
                cerca = [g for _, g in tramo]
            else:
                hallados.sort(key=lambda x: abs(x[0] - ancla))
                cerca = [hallados[0][1]] if abs(hallados[0][0] - ancla) < 250 else []
        else:
            cerca = [g for _, g in hallados]
        out = []
        for g in cerca:
            if g == "A":
                g = "A1/A2"
            if g == "C":
                g = "C1/C2"
            if g not in out:
                out.append(g)
        # "Grupo A, subgrupo A2": quitamos el genérico si hay subgrupo concreto
        if "A1/A2" in out and ("A1" in out or "A2" in out):
            out.remove("A1/A2")
        if "C1/C2" in out and ("C1" in out or "C2" in out):
            out.remove("C1/C2")
        return out, False
    for g, rx in INFER:
        if re.search(rx, t):
            return [g], True
    return [], False


# ---------------------------------------------------------------- zona
CANTABRIA = ["cantabria", "cantabro", "santander", "torrelavega", "camargo", "castro urdiales", "pielagos",
             "laredo", "reinosa", "santona", "astillero", "los corrales de buelna", "pielagos", "suances",
             "medio cudeyo", "santa cruz de bezana", "colindres", "cabezon de la sal", "comillas", "noja",
             "ramales de la victoria", "san vicente de la barquera", "piélagos", "valdaliga", "marina de cudeyo"]
LIMITROFE = ["asturias", "principado", "oviedo", "gijon", "aviles", "langreo", "mieres", "siero",
             "burgos", "palencia", "leon", "ponferrada", "miranda de ebro", "aguilar de campoo",
             "castilla y leon", "bizkaia", "vizcaya", "bilbao", "barakaldo", "getxo", "basauri", "portugalete",
             "pais vasco", "euskadi", "euskal herriko", "upv/ehu", "osakidetza"]
CERCANA = ["valladolid", "zamora", "salamanca", "segovia", "soria", "avila", "alava", "araba", "vitoria",
           "gipuzkoa", "guipuzcoa", "donostia", "san sebastian", "rioja", "logrono", "navarra", "pamplona",
           "lugo", "ourense", "orense", "coruna", "pontevedra", "vigo", "galicia", "xunta",
           "santiago de compostela", "ferrol"]
ESTATAL = ["ministerio", "administracion del estado", "administracion general del estado", "agencia estatal",
           "agencia tributaria", "seguridad social", "consejo general del poder judicial", "cortes generales",
           "congreso de los diputados", "senado", "tribunal constitucional", "tribunal de cuentas", "banco de espana",
           "comision nacional", "consejo de seguridad nuclear", "defensor del pueblo", "csic",
           "consejo superior de investigaciones"]


def _hay(lista, t):
    for w in lista:
        if re.search(r"\b" + re.escape(w) + r"\b", t):
            return w
    return None


def detectar_zona(titulo_n, organismo_n, texto_n, fuente_zona=None):
    if fuente_zona:
        return fuente_zona
    # 1) provincia entre paréntesis en el título: "Ayuntamiento de Camargo (Cantabria)"
    for par in re.findall(r"\(([^)]{3,40})\)", titulo_n):
        for zona, lista in (("cantabria", CANTABRIA), ("limitrofe", LIMITROFE), ("cercana", CERCANA)):
            if _hay(lista, par):
                return zona
    for bloque in (titulo_n + " " + organismo_n, texto_n[:700]):
        for zona, lista in (("cantabria", CANTABRIA), ("limitrofe", LIMITROFE), ("cercana", CERCANA)):
            if _hay(lista, bloque):
                return zona
        if _hay(ESTATAL, bloque):
            return "estatal"
    if re.search(r"\(([^)]{3,40})\)", titulo_n) or "ayuntamiento" in titulo_n or "universidad" in titulo_n:
        return "resto"
    return "desconocida"


# ---------------------------------------------------------------- plazo
NUM = {"cinco": 5, "diez": 10, "quince": 15, "veinte": 20, "treinta": 30, "un mes": 30, "veinticinco": 25,
       "doce": 12, "catorce": 14, "siete": 7, "ocho": 8, "nueve": 9, "seis": 6}
PLAZO_RX = re.compile(
    r"plazo (de presentacion )?de (las )?(solicitudes|instancias)[^.]{0,40}?"
    r"(\d{1,2}|cinco|seis|siete|ocho|nueve|diez|doce|catorce|quince|veinte|veinticinco|treinta)\s*(\(\d+\)\s*)?dias (naturales|habiles)"
    r"([^.]{0,200})")


def detectar_plazo(t, fecha_pub: dt.date, fuente: str):
    m = PLAZO_RX.search(t)
    if not m:
        return "", None
    n = m.group(4)
    n = int(n) if n.isdigit() else NUM.get(n, 0)
    clase = m.group(6)
    cola = m.group(7) or ""
    txt = f"{n} días {clase}"
    if fuente != "BOE" and "boletin oficial del estado" in cola:
        return txt + " desde el extracto en el BOE (aún por publicar)", None
    if not n or not fecha_pub:
        return txt, None
    d, k = fecha_pub, 0
    while k < n:
        d += dt.timedelta(days=1)
        if clase == "naturales" or d.weekday() < 5:
            k += 1
    return txt + (" (aprox., sin festivos)" if clase == "habiles" else ""), d.isoformat()


# ---------------------------------------------------------------- organismo
ORG_RX = re.compile(
    r"\b(?:del|de la|de los|de las)\s+((?:excmo\.?\s+)?(?:ayuntamiento|universidad|universitat|universidade|diputaci[oó]n|"
    r"cabildo|consell|mancomunidad|consejer[ií]a|ministerio|agencia|instituto|servicio|fundacion|consorcio|"
    r"gerencia|junta|comarca|parlamento|tribunal|comunidad|entidad|organismo|empresa|sociedad|"
    r"direcci[oó]n general|secretar[ií]a de estado|secretar[ií]a general|subsecretar[ií]a|presidencia)[^,;]{2,120}?)(?=,| por la que| referente| sobre|$)", re.I)


def detectar_organismo(titulo, departamento=""):
    m = ORG_RX.search(titulo)
    if m:
        org = m.group(1).strip()
        return org[0].upper() + org[1:]
    return _capitalizar(departamento or "")


def _capitalizar(s):
    menores = {"de", "del", "la", "las", "los", "el", "y", "e", "para", "en", "a"}
    pal = s.lower().split()
    return " ".join(p if (i and p in menores) else p[:1].upper() + p[1:] for i, p in enumerate(pal))


# ---------------------------------------------------------------- puntuación
DEFAULT_PESOS = {
    "zona": {"cantabria": 35, "limitrofe": 25, "estatal": 22, "cercana": 15, "resto": 5, "desconocida": 10},
    "sistema": {"oposicion": 20, "concurso-oposicion": 12, "concurso": 4, "desconocido": 9},
    "vinculo": {"funcionario": 20, "laboral": 10, "temporal": 2, "desconocido": 9},
    "grupo_ok": 15, "grupo_desconocido": 7, "grupo_fuera": -45,
    "tipo": {"convocatoria": 10, "oep": 6, "seguimiento": 2, "correccion": 2, "provision": 0, "otro": 1},
    "penal_promocion_interna": -30,
    # los anuncios que no abren plazo (listas, tribunales, correcciones...) se rebajan para no competir con convocatorias
    "factor_tipo": {"seguimiento": 0.6, "correccion": 0.6, "provision": 0.3, "otro": 0.5},
    "niveles": {"prioritaria": 75, "interesante": 55, "vigilar": 35},
}
ETQ_ZONA = {"cantabria": "Cantabria", "limitrofe": "Limítrofe", "estatal": "Estatal (AGE)", "cercana": "Norte cercano",
            "resto": "Resto de España", "desconocida": "Zona ?"}
ETQ_SIS = {"oposicion": "Oposición", "concurso-oposicion": "Concurso-oposición", "concurso": "Concurso", None: "Sistema ?"}
ETQ_VIN = {"funcionario": "Funcionario de carrera", "laboral": "Laboral fijo", "temporal": "Temporal / bolsa", None: "Vínculo ?"}
ETQ_TIPO = {"convocatoria": "Convocatoria", "oep": "Oferta de empleo", "seguimiento": "Fase del proceso",
            "correccion": "Corrección / modificación", "provision": "Provisión de puestos", "otro": "Otro"}


def _merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def puntuar(c, pesos=None, grupos_ok=("A1", "A2", "B", "C1")):
    P = _merge(DEFAULT_PESOS, pesos or {})
    d = []
    z = P["zona"].get(c["zona"], 5)
    d.append((ETQ_ZONA.get(c["zona"], c["zona"]), z))
    s = P["sistema"].get(c["sistema"] or "desconocido", 9)
    d.append((ETQ_SIS[c["sistema"]], s))
    v = P["vinculo"].get(c["vinculo"] or "desconocido", 9)
    d.append((ETQ_VIN[c["vinculo"]], v))
    grupos = c["grupos"]
    ok = set(grupos_ok)
    if not grupos:
        g, etq = P["grupo_desconocido"], "Grupo ?"
    else:
        expand = set()
        for x in grupos:
            expand.update(x.split("/"))
        if expand & ok:
            g, etq = P["grupo_ok"], "Grupo " + "/".join(grupos) + (" (deducido)" if c.get("grupo_inferido") else "")
        else:
            g, etq = P["grupo_fuera"], "Grupo " + "/".join(grupos) + " (fuera de tu rango)"
    d.append((etq, g))
    t = P["tipo"].get(c["tipo"], 1)
    d.append((ETQ_TIPO.get(c["tipo"], c["tipo"]), t))
    if c["acceso"] == "interna":
        d.append(("Sólo promoción interna", P["penal_promocion_interna"]))
    total = sum(x for _, x in d)
    f = P["factor_tipo"].get(c["tipo"])
    if f is not None and total > 0:
        d.append((f"× {f} (no abre plazo)", round(total * f) - total))
        total = round(total * f)
    total = max(0, min(100, total))
    n = P["niveles"]
    nivel = "prioritaria" if total >= n["prioritaria"] else "interesante" if total >= n["interesante"] \
        else "vigilar" if total >= n["vigilar"] else "baja"
    return total, nivel, d


def clasificar(titulo, texto="", departamento="", fuente="BOE", fecha_pub=None, fuente_zona=None,
               extra_kw=(), pesos=None, grupos_ok=("A1", "A2", "B", "C1"), zona_defecto=None):
    """Devuelve dict con todo, o None si no es de informática."""
    tn, xn, dn = norm(titulo), norm(texto), norm(departamento)
    es_it, ancla, frag = detectar_it(tn, xn, extra_kw)
    if not es_it:
        return None
    # Si la informática sólo aparece en el cuerpo (título genérico tipo "...para proveer varias plazas"),
    # exigimos una plaza/cuerpo concreto de informática: evita los "experiencia en sistemas de información" de
    # convocatorias de médicos, administrativos, etc.
    if not detectar_it(tn, "", extra_kw)[0] and not detectar_puesto(titulo, texto) and \
            not any(kw and norm(kw) in xn for kw in extra_kw):
        return None
    todo = tn + " \n " + xn  # el título va delante: posiciones del texto desplazadas
    off = len(tn) + 3
    ancla_t = (ancla + off) if (ancla is not None and ancla >= 0) else None
    c = {
        "tipo": detectar_tipo(tn, xn),
        "sistema": detectar_sistema(todo, ancla_t),
        "vinculo": detectar_vinculo(todo, ancla_t),
        "acceso": detectar_acceso(todo),
        "zona": detectar_zona(tn, dn, xn, fuente_zona),
        "organismo": detectar_organismo(titulo, departamento),
    }
    if c["zona"] == "desconocida" and zona_defecto:
        c["zona"] = zona_defecto
    c["grupos"], c["grupo_inferido"] = detectar_grupo(todo, ancla_t)
    c["plazo_txt"], c["plazo_fin"] = detectar_plazo(xn, fecha_pub, fuente) if c["tipo"] in ("convocatoria",) else ("", None)
    c["detalle"] = _detalle(texto, ancla) or ""
    c["puesto"] = detectar_puesto(titulo, texto)
    c["escala"] = detectar_escala(todo, ancla_t)
    c["lugar"], c["km"] = lugar_y_km(c["organismo"], titulo, c["zona"])
    c["score"], c["nivel"], c["desglose"] = puntuar(c, pesos, grupos_ok)
    return c


def _detalle(texto, ancla_norm):
    """Fragmento legible (con tildes) alrededor de la plaza. Las posiciones normalizadas casi coinciden."""
    if not texto or ancla_norm is None or ancla_norm < 0:
        return ""
    flat = re.sub(r"\s+", " ", texto)
    a = max(0, ancla_norm - 80)
    frag = flat[a:ancla_norm + 260]
    # cortar en límites de palabra
    frag = re.sub(r"^\S*\s", "", frag) if a else frag
    frag = re.sub(r"\s\S*$", "", frag)
    return ("…" if a else "") + frag.strip() + "…"


# ---------------------------------------------------------------- puesto y escala (para el titular)
PUESTO_RX = re.compile(
    r"(?:plazas?|puestos?|categor[ií]as?(?: profesional)?|especialidad)\s+(?:de\s+|del\s+|denominad[ao]s?\s+)?"
    r"[«\"“]?([^,.;:()\n«»\"“”]{4,90})", re.I)
CUERPO_RX = re.compile(r"\b((?:cuerpo|escala|subescala)\s+(?:de\s+|del\s+)?[^,.;:()\n]{4,90})", re.I)


def _es_it_txt(s):
    n = _limpiar_ruido(norm(s))
    return bool(IT_FUERTE_RE.search(n))


def _limpiar_puesto(p):
    p = re.sub(r"\s+", " ", p).strip(" -–«»\"“”")
    p = re.sub(r"\s+(perteneciente|vacante|incluida|encuadrad|de la plantilla|en la plantilla|mediante|por el sistema|"
               r"como personal|con destino|para el|en r[eé]gimen|de personal|con car[aá]cter|grupo|subgrupo|nivel).*$",
               "", p, flags=re.I)
    p = re.sub(r"\s+de la administraci[oó]n (general )?del estado$", "", p.strip(" ,-"), flags=re.I)
    return p[:80]


def detectar_puesto(titulo, texto=""):
    """'Técnico/a Informático/a', 'Cuerpo de Gestión de Sistemas e Informática'..."""
    for fuente in (titulo, texto[:3000]):
        for m in PUESTO_RX.finditer(fuente or ""):
            if _es_it_txt(m.group(1)):
                p = _limpiar_puesto(m.group(1))
                if len(p) >= 4:
                    return p
        for m in CUERPO_RX.finditer(fuente or ""):
            if _es_it_txt(m.group(1)):
                p = _limpiar_puesto(m.group(1))
                if len(p) >= 4:
                    return p[0].upper() + p[1:]
    # en el cuerpo, una mención directa del puesto ("Técnico Informático", "Técnico/a de Sistemas", "Analista Programador")
    m = re.search(r"\b(t[eé]cnic[oa]s?(?:/a)?\s+(?:\w+(?:/a)?\s+){0,2}?(?:inform[aá]tic\w*(?:/a)?|de sistemas\b|en sistemas\b|tic\b)|"
                  r"analistas?(?:/a)? programador\w*|programador\w*(?:/a)?(?: \w+)?|operador\w*(?:/a)? de (?:ordenador|sistemas)\w*)",
                  texto[:6000] if texto else "", re.I)
    if m:
        return _limpiar_puesto(m.group(1))
    # último recurso: la frase de informática del título
    n = _limpiar_ruido(titulo or "")
    m = re.search(r"(t[eé]cnic\w*(?:/a)?\s+(?:\w+\s+){0,3}?(?:inform[aá]tic\w*(?:/a)?|sistemas\w*)|"
                  r"programador\w*|analista\w*(?: \w+)?|inform[aá]tic\w*)", n, re.I)
    return _limpiar_puesto(m.group(1)) if m else ""


ESCALA_RX = re.compile(r"escala de (administracion (especial|general))(?:\W+subescala (\w+))?(?:\W+(?:y\s+)?clase (\w+))?")


def detectar_escala(t, ancla):
    ms = list(ESCALA_RX.finditer(t))
    if not ms:
        return ""
    if ancla is not None and ancla >= 0:
        ms.sort(key=lambda m: abs(m.start() - ancla))
    m = ms[0]
    partes = ["Adm. " + m.group(2).capitalize()]
    if m.group(3):
        partes.append(m.group(3).capitalize())
    if m.group(4):
        partes.append("clase " + m.group(4))
    return " · ".join(partes)
