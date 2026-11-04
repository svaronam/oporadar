import copy
import json
import os

DEFAULT = {
    "host": "0.0.0.0",
    "puerto": 8790,
    "token": "",
    "grupos": ["A1", "A2", "B", "C1"],
    "hora_barrida": "09:20",
    "vigilar_cada_horas": 4,
    "dias_atras": 4,
    "fuentes": {"boe": True, "boc": True, "bocyl": True, "bopa": True, "bopv": True},
    "boc_url_plantilla": "",
    "rss": [],
    "palabras_extra": [],
    "pesos": {},
    "notificar": {"niveles": ["prioritaria", "interesante", "vigilar"], "tipos": ["convocatoria", "oep"]},
    "pausa_entre_peticiones": 0.4,
}


def _merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def cargar(base_dir):
    path = os.path.join(base_dir, "config.json")
    user = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
    cfg = _merge(DEFAULT, {k: v for k, v in user.items() if not k.startswith("_")})
    if os.environ.get("OPORADAR_PUERTO"):  # p. ej. para probar en el PC con otro puerto
        cfg["puerto"] = int(os.environ["OPORADAR_PUERTO"])
    cfg["data_dir"] = os.path.join(base_dir, "data")
    os.makedirs(cfg["data_dir"], exist_ok=True)
    return cfg
