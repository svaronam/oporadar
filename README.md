# OpoRadar

Radar diario de **oposiciones de informática** en boletines oficiales españoles. Un servidor en Python lee cada mañana el BOE y varios boletines autonómicos, filtra solo las plazas TIC, las puntúa de 0 a 100 según su interés y envía avisos a una app Android propia.

## Qué hace

- **Lee 5 boletines oficiales**: BOE (API oficial, sección II.B), BOC (Cantabria), BOPA (Asturias), BOCYL (Castilla y León) y BOPV (País Vasco), más fuentes RSS opcionales.
- **Clasifica** cada anuncio: detecta si es de informática (técnico, sistemas, TIC, programador, ciberseguridad…), el grupo (A1, A2, B, C1), el sistema de acceso y el tipo de anuncio (convocatoria, oferta de empleo, lista de admitidos…).
- **Puntúa** de 0 a 100 con un baremo configurable (zona, sistema de acceso, tipo de plaza, grupo) y explica de dónde sale cada punto.
- **Sigue convocatorias**: vigila las páginas de las convocatorias a las que te apuntas y avisa cuando aparece un documento nuevo (listas, fechas de examen…).
- **Se autovigila**: si un boletín falla o pasa varios días sin anuncios (señal de que su web ha cambiado), lanza una alerta de estado. Lo que falla se reintenta hasta 14 días.
- **Calcula la distancia** aproximada por carretera a cada plaza con una tabla interna, sin servicios externos.

## Arquitectura

```
 BOE · BOC · BOPA · BOCYL · BOPV · RSS
                 │  barrida diaria + reintentos
                 ▼
        Servidor Python (Raspberry Pi)
        ├─ lectores por boletín (sources/)
        ├─ clasificador y baremo (classify.py)
        ├─ vigilancia de convocatorias (vigilar.py)
        ├─ SQLite
        └─ API HTTP + panel web
                 │  Tailscale (VPN)
                 ▼
          App Android (Kotlin)
          avisos nativos por prioridad
```

## Tecnologías

- **Backend**: Python 3, solo biblioteca estándar (`http.server`, `urllib`, `sqlite3`, `xml`), sin dependencias externas para que corra ligero en una Raspberry Pi 3.
- **Tests**: `unittest`, con casos sobre HTML real de cada boletín.
- **App**: Android nativo en Kotlin.
- **CI/CD**: GitHub Actions compila y publica la APK en cada push.
- **Infraestructura**: Raspberry Pi, servicio `systemd`, acceso remoto por Tailscale.

## Estructura

```
server/
  oporadar/sources/   lectores de cada boletín
  oporadar/classify.py   clasificación y baremo
  oporadar/vigilar.py    seguimiento de convocatorias
  oporadar/web.py        API y panel
  tests/                 tests de lectores, clasificación y escaneo
android/               app Android
.github/workflows/     compilación de la APK
```

## Puesta en marcha

```bash
cd server
cp config.example.json config.json   # ajusta grupos, fuentes y baremo
python3 run.py
python3 -m unittest discover tests   # tests
```

La guía completa (servicio en la Raspberry, compilar la APK, configuración del baremo) está en [INSTALACION.md](INSTALACION.md).
