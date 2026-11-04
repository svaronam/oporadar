"""Lugar de la plaza y distancia aproximada desde Santander (sin internet: tabla de capitales y pueblos de Cantabria)."""
import math
import re

from .util import norm

SANTANDER = (43.4623, -3.8100)
FACTOR_CARRETERA = 1.15  # línea recta -> carretera, aproximado

# provincia / ciudad -> (nombre bonito, lat, lon)
SITIOS = {
    "a coruna": ("A Coruña", 43.362, -8.411), "coruna": ("A Coruña", 43.362, -8.411), "ferrol": ("Ferrol", 43.483, -8.236),
    "santiago de compostela": ("Santiago", 42.878, -8.544), "lugo": ("Lugo", 43.012, -7.556),
    "ourense": ("Ourense", 42.336, -7.864), "orense": ("Ourense", 42.336, -7.864), "pontevedra": ("Pontevedra", 42.431, -8.644),
    "vigo": ("Vigo", 42.240, -8.721), "galicia": ("Galicia", 42.878, -8.544), "xunta": ("Galicia", 42.878, -8.544),
    "asturias": ("Asturias", 43.361, -5.849), "principado": ("Asturias", 43.361, -5.849), "oviedo": ("Oviedo", 43.361, -5.849),
    "gijon": ("Gijón", 43.532, -5.661), "aviles": ("Avilés", 43.556, -5.925), "mieres": ("Mieres", 43.250, -5.777),
    "langreo": ("Langreo", 43.297, -5.693), "siero": ("Siero", 43.389, -5.663),
    "leon": ("León", 42.599, -5.567), "ponferrada": ("Ponferrada", 42.546, -6.598), "villaquilambre": ("Villaquilambre", 42.629, -5.548),
    "burgos": ("Burgos", 42.344, -3.697), "miranda de ebro": ("Miranda de Ebro", 42.685, -2.947),
    "palencia": ("Palencia", 42.010, -4.528), "aguilar de campoo": ("Aguilar de Campoo", 42.794, -4.258),
    "valladolid": ("Valladolid", 41.652, -4.724), "medina del campo": ("Medina del Campo", 41.311, -4.914),
    "castilla y leon": ("Castilla y León", 41.652, -4.724),
    "zamora": ("Zamora", 41.503, -5.744), "salamanca": ("Salamanca", 40.970, -5.663),
    "segovia": ("Segovia", 40.942, -4.109), "soria": ("Soria", 41.764, -2.465), "avila": ("Ávila", 40.656, -4.700),
    "bizkaia": ("Bizkaia", 43.263, -2.935), "vizcaya": ("Bizkaia", 43.263, -2.935), "bilbao": ("Bilbao", 43.263, -2.935),
    "barakaldo": ("Barakaldo", 43.297, -2.989), "getxo": ("Getxo", 43.356, -3.012),
    "alava": ("Álava", 42.846, -2.672), "araba": ("Álava", 42.846, -2.672), "vitoria": ("Vitoria", 42.846, -2.672),
    "gipuzkoa": ("Gipuzkoa", 43.318, -1.981), "guipuzcoa": ("Gipuzkoa", 43.318, -1.981),
    "donostia": ("Donostia", 43.318, -1.981), "san sebastian": ("Donostia", 43.318, -1.981),
    "pais vasco": ("País Vasco", 42.846, -2.672), "euskadi": ("País Vasco", 42.846, -2.672), "euskal herriko": ("País Vasco", 43.263, -2.935),
    "la rioja": ("La Rioja", 42.465, -2.445), "rioja": ("La Rioja", 42.465, -2.445), "logrono": ("Logroño", 42.465, -2.445),
    "navarra": ("Navarra", 42.812, -1.646), "pamplona": ("Pamplona", 42.812, -1.646),
    "huesca": ("Huesca", 42.140, -0.408), "zaragoza": ("Zaragoza", 41.649, -0.889), "tarazona": ("Tarazona", 41.905, -1.725),
    "teruel": ("Teruel", 40.346, -1.106), "aragon": ("Aragón", 41.649, -0.889),
    "barcelona": ("Barcelona", 41.388, 2.170), "pompeu fabra": ("Barcelona", 41.388, 2.170), "girona": ("Girona", 41.979, 2.821),
    "gerona": ("Girona", 41.979, 2.821), "lleida": ("Lleida", 41.617, 0.620), "lerida": ("Lleida", 41.617, 0.620),
    "tarragona": ("Tarragona", 41.119, 1.245), "rovira i virgili": ("Tarragona", 41.119, 1.245), "cataluna": ("Cataluña", 41.388, 2.170),
    "catalunya": ("Cataluña", 41.388, 2.170), "generalitat de catalunya": ("Cataluña", 41.388, 2.170),
    "madrid": ("Madrid", 40.417, -3.704), "complutense": ("Madrid", 40.417, -3.704), "carlos iii": ("Madrid", 40.332, -3.766),
    "rey juan carlos": ("Madrid", 40.336, -3.874), "alcala": ("Alcalá de Henares", 40.482, -3.364),
    "boadilla del monte": ("Boadilla del Monte", 40.405, -3.878), "boadilla": ("Boadilla del Monte", 40.405, -3.878),
    "getafe": ("Getafe", 40.305, -3.732), "mostoles": ("Móstoles", 40.322, -3.865), "leganes": ("Leganés", 40.328, -3.764),
    "alcobendas": ("Alcobendas", 40.547, -3.642), "las rozas": ("Las Rozas", 40.493, -3.874), "pozuelo": ("Pozuelo", 40.435, -3.814),
    "guadalajara": ("Guadalajara", 40.633, -3.167), "toledo": ("Toledo", 39.863, -4.027), "cuenca": ("Cuenca", 40.070, -2.137),
    "ciudad real": ("Ciudad Real", 38.985, -3.927), "albacete": ("Albacete", 38.994, -1.858), "castilla-la mancha": ("Castilla-La Mancha", 39.863, -4.027),
    "castilla la mancha": ("Castilla-La Mancha", 39.863, -4.027),
    "caceres": ("Cáceres", 39.475, -6.372), "badajoz": ("Badajoz", 38.879, -6.970), "merida": ("Mérida", 38.916, -6.344),
    "extremadura": ("Extremadura", 38.916, -6.344),
    "valencia": ("Valencia", 39.470, -0.376), "castellon": ("Castellón", 39.986, -0.051), "jaume i": ("Castellón", 39.986, -0.051),
    "alicante": ("Alicante", 38.345, -0.481), "miguel hernandez": ("Elche", 38.267, -0.698), "elche": ("Elche", 38.267, -0.698),
    "comunitat valenciana": ("C. Valenciana", 39.470, -0.376), "generalitat valenciana": ("C. Valenciana", 39.470, -0.376),
    "murcia": ("Murcia", 37.992, -1.130), "cartagena": ("Cartagena", 37.605, -0.986),
    "sevilla": ("Sevilla", 37.389, -5.984), "pablo de olavide": ("Sevilla", 37.389, -5.984), "cordoba": ("Córdoba", 37.888, -4.779),
    "jaen": ("Jaén", 37.779, -3.784), "granada": ("Granada", 37.177, -3.599), "almeria": ("Almería", 36.834, -2.464),
    "malaga": ("Málaga", 36.721, -4.421), "cadiz": ("Cádiz", 36.527, -6.289), "huelva": ("Huelva", 37.261, -6.945),
    "andalucia": ("Andalucía", 37.389, -5.984), "junta de andalucia": ("Andalucía", 37.389, -5.984),
    "baleares": ("Baleares", 39.570, 2.650), "illes balears": ("Baleares", 39.570, 2.650), "mallorca": ("Mallorca", 39.570, 2.650),
    "ibiza": ("Ibiza", 38.909, 1.433), "menorca": ("Menorca", 39.889, 4.262),
    "las palmas": ("Las Palmas", 28.124, -15.430), "gran canaria": ("Gran Canaria", 28.124, -15.430),
    "santa cruz de tenerife": ("Tenerife", 28.464, -16.251), "tenerife": ("Tenerife", 28.464, -16.251), "canarias": ("Canarias", 28.124, -15.430),
    "ceuta": ("Ceuta", 35.889, -5.321), "melilla": ("Melilla", 35.292, -2.938),
}
# Cantabria: km por carretera aproximados desde Santander
CANTABRIA_KM = {
    "santander": 0, "santa cruz de bezana": 7, "bezana": 7, "camargo": 8, "el astillero": 8, "astillero": 8,
    "villaescusa": 15, "pielagos": 15, "medio cudeyo": 18, "marina de cudeyo": 18, "polanco": 22, "torrelavega": 25,
    "entrambasaguas": 25, "cartes": 28, "suances": 30, "los corrales de buelna": 38, "corrales de buelna": 38,
    "noja": 40, "santona": 45, "colindres": 45, "cabezon de la sal": 45, "laredo": 48, "comillas": 50, "ampuero": 50,
    "ramales de la victoria": 60, "san vicente de la barquera": 65, "castro urdiales": 70, "reinosa": 75,
    "campoo de enmedio": 75, "potes": 115, "valdaliga": 55, "voto": 40, "argonos": 40, "bareyo": 35, "ribamontan al mar": 25,
    "universidad de cantabria": 0, "cantabria": 0,
}


def _km(lat, lon):
    la1, lo1 = map(math.radians, SANTANDER)
    la2, lo2 = math.radians(lat), math.radians(lon)
    a = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return round(2 * 6371 * math.asin(math.sqrt(a)) * FACTOR_CARRETERA / 5) * 5


def _buscar(t, tabla):
    # el término más largo primero ("ciudad real" antes que "real", "santa cruz de bezana" antes que "bezana")
    for k in sorted(tabla, key=len, reverse=True):
        if re.search(r"\b" + re.escape(k) + r"\b", t):
            return k
    return None


MUNI_RX = re.compile(r"^(?:excmo\.?\s+)?(?:ayuntamiento|concello|ajuntament|udala|mancomunidad|comarca|diputaci[oó]n( provincial)?|"
                     r"cabildo( insular)?|consell( insular)?|universidad|universitat|universidade)\s+(?:de\s+|del\s+|d')?(?P<sitio>.+)$", re.I)


def lugar_y_km(organismo, titulo="", zona=""):
    """Devuelve (lugar legible, km aprox. desde Santander o None)."""
    org = (organismo or "").strip()
    lugar = org
    m = MUNI_RX.match(org)
    if m:
        lugar = m.group("sitio").strip()
    if zona == "estatal":
        return "Estatal (AGE)", None
    t = norm(org + " " + titulo)
    if zona == "cantabria" or "cantabria" in t:
        sin_par = norm(re.sub(r"\([^)]*\)", "", lugar))
        k = _buscar(sin_par, CANTABRIA_KM) or _buscar(t, {x: v for x, v in CANTABRIA_KM.items() if x != "cantabria"}) \
            or _buscar(t, CANTABRIA_KM)
        km = CANTABRIA_KM.get(k) if k else None
        nombre = re.sub(r"\s*\(cantabria\)\s*", "", lugar, flags=re.I).strip() or "Cantabria"
        if norm(nombre) in ("gobierno de cantabria", "comunidad autonoma de cantabria") or not m:
            nombre = nombre if m else "Cantabria"
        return nombre, km
    # primero el propio municipio si lo conocemos (Tarazona), luego su provincia entre paréntesis
    k = _buscar(norm(re.sub(r"\([^)]*\)", "", lugar)), SITIOS) if m else None
    if k:
        _, la, lo = SITIOS[k]
        return lugar, _km(la, lo)
    par = re.findall(r"\(([^)]{3,40})\)", lugar + " " + (titulo or ""))
    for p in par:
        k = _buscar(norm(p), SITIOS)
        if k:
            _, la, lo = SITIOS[k]
            return lugar, _km(la, lo)
    k = _buscar(norm(lugar), SITIOS) or _buscar(t, SITIOS)
    if k:
        nombre, la, lo = SITIOS[k]
        return (lugar if m else nombre), _km(la, lo)
    return (lugar if m else ""), None
