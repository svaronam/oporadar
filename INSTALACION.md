# OpoRadar

Vigila cada día los boletines oficiales, se queda **solo con las oposiciones de informática** (técnico informático, sistemas, TIC, programador, analista, ciberseguridad, GSI…) de los grupos **A1, A2, B y C1**, las puntúa de 0 a 100 según lo que te conviene y te avisa en el móvil por Tailscale.

```
oporadar/
├── server/        → Python para la Raspberry (sin dependencias externas)
├── android/       → APK (se compila sola en GitHub Actions)
└── .github/workflows/apk.yml
```

## Qué fuentes mira

| Fuente | Qué cubre | Por qué |
|---|---|---|
| **BOE · II.B Oposiciones y concursos** (API oficial) | AGE (GSI, TAI, Superior TIC…), universidades y el **extracto de todas las convocatorias de funcionarios de ayuntamientos y diputaciones de España** | La ley obliga a publicar ese extracto en el BOE y desde él cuenta el plazo, así que por aquí no se escapa ninguna local |
| **BOC · 2.2 y 2.3** (Cantabria) | Gobierno de Cantabria, UC, SCS, los 102 ayuntamientos, mancomunidades | Las bases salen aquí **antes** que el extracto del BOE |
| **BOPA** (Asturias) | Principado, SESPA, Universidad de Oviedo y ayuntamientos asturianos | Las convocatorias propias del Principado no siempre llegan al BOE |
| **BOCYL** (Castilla y León) | Junta de CyL, Sacyl, universidades de León, Burgos, Valladolid y Salamanca, ayuntamientos | Ídem |
| **BOPV** (País Vasco) | Gobierno Vasco, IVAP, Osakidetza, UPV/EHU, ayuntamientos y diputaciones vascas | Ídem |
| RSS opcionales (`config.json → rss`) | Lo que quieras añadir | Por si sigues una web concreta con RSS |

Los cuatro lectores autonómicos se escribieron mirando las webs reales (octubre de 2026). Cada día se revisan los últimos 4 días, y lo que falle (web caída, anuncio que no se puede leer, boletín aún sin publicar) **se reintenta hasta 14 días**.

**Alertas ⚠:** si un boletín da error o pasa 3 de 5 días laborables sin un solo anuncio de oposiciones (señal de que su web ha cambiado), te llega una notificación «⚠ Estado del radar» y aparece un aviso en la web. Así no te quedas sin una fuente sin enterarte.

**Lo que sigue sin cubrirse:** convocatorias propias de las otras 13 comunidades autónomas que no envían extracto al BOE, empresas públicas y fundaciones (Sodercan, EJIE…), y bolsas de interinos que solo salen en un boletín provincial. Para una web concreta que te interese, usa 📌 Apuntado → vigilar página.

## Cómo se ve cada anuncio

Arriba, en grande: **GRUPO · PUESTO · LUGAR** (p. ej. `A2 · TÉCNICO/A INFORMÁTICO/A · ALHAMBRA (CIUDAD REAL)`), y debajo los **km aproximados por carretera desde Santander**, el organismo y la escala/subescala si viene. Los km salen de una tabla interna (capitales de provincia, municipios grandes y pueblos de Cantabria), así que son orientativos.

## 📌 Apuntado

La pestaña para las convocatorias en las que te has presentado:

1. Pulsa **📌 Me apunto** en cualquier anuncio del Radar, o **＋ Añadir convocatoria a mano** para las que ya seguías (Tarazona, Gijón, Boadilla, Villaquilambre…).
2. Pega la **URL de la página de esa convocatoria** (la carpeta de la sede electrónica, el portal de empleo del ayuntamiento o universidad…). Puedes poner varias.
3. La Pi la revisa **cada 4 horas** (de 7 a 23 h). La primera vez guarda los documentos que ya hay (salen en «Documentos que ya había»); cada **PDF o enlace nuevo** aparece como **NUEVO** y te llega una notificación «📌 A2 · Técnico de Informática · Tarazona — Nuevo documento: Lista provisional de admitidos».
4. Además, si en el **BOE o BOC** sale algo de informática del mismo organismo (lista de admitidos, tribunal, fecha de examen, el extracto que abre plazo…), se añade solo a esa ficha.

Si una página dice «No veo documentos», es que la web carga la lista con JavaScript: abre la carpeta/listado concreto y pega esa URL. El HTML que ve la Pi queda en `server/data/debug/vigilancia_N.html` por si hay que afinar.

## El gradiente

| Criterio | Puntos |
|---|---|
| Zona: Cantabria · limítrofe (Asturias, Burgos, Palencia, León, Bizkaia, País Vasco, Junta de CyL) · estatal (AGE) · norte cercano (resto de CyL, Álava, Gipuzkoa, La Rioja, Navarra, Galicia) · resto | 35 · 25 · 22 · 15 · 5 |
| Oposición · concurso-oposición · concurso | 20 · 12 · 4 |
| Funcionario de carrera · laboral fijo · temporal/bolsa | 20 · 10 · 2 |
| Grupo A1/A2/B/C1 · sin indicar · fuera de rango (C2, E) | 15 · 7 · −45 |
| Convocatoria · oferta de empleo público · fase/corrección | 10 · 6 · 2 |
| Solo promoción interna | −30 |
| Listas de admitidos, tribunales, correcciones (no abren plazo) | × 0,6 |

**🔴 Prioritaria ≥ 75** (suena, aparece arriba) · **🟠 Interesante ≥ 55** (aviso normal) · **🔵 A vigilar ≥ 35** (aviso silencioso) · **Baja < 35** (solo en la lista).

Ejemplos: técnico informático A2 por oposición en un ayuntamiento de Cantabria = 100 · GSI de la AGE = 87 · técnico auxiliar de informática C1 en Gijón por concurso-oposición = 82 · laboral fijo en la Universidad de Sevilla por concurso-oposición = 52.

Todo es ajustable en `server/config.json → pesos` (sin tocar código). En la web/app, toca el número de cualquier anuncio para ver de dónde salen sus puntos.

---

## 1 · Servidor en la Raspberry

Recomendado en **homelab2** (homelab1 ya tiene el de Wallapop en el 8787; este usa el **8790**).

```bash
# en el PC: sube la carpeta (o clónala desde tu repo)
scp -r oporadar/server usuario@homelab2:~/oporadar

# en la Pi
ssh usuario@homelab2
cd ~/oporadar
bash install.sh                         # instala el servicio systemd y lo arranca
python3 run.py probar                   # ¿leen bien los 5 boletines? (resumen al final)
python3 run.py barrida --dias 30        # primera vez: rellena el último mes
```

Desde ahí, el servicio hace **una barrida al día a las 09:20** (y al arrancar recupera los días que la Pi estuvo apagada, hasta 4 atrás). También puedes lanzarla con el botón **Barrer ahora**.

Prueba en el navegador del móvil, con Tailscale activo: `http://homelab2:8790`

Útil:
```bash
journalctl -u oporadar -f               # log en vivo
sudo systemctl restart oporadar         # tras cambiar config.json
```

### Si `probar` da 0 anuncios o ERROR en algún boletín un día laborable
Los boletines autonómicos no tienen API y los lectores van por el HTML de sus webs. Copia lo que sale por pantalla (y, del BOC, `data/debug/boc_sumario.html`) y pásamelo para ajustarlo. Mientras tanto, el BOE sigue cubriendo las convocatorias locales con el extracto, algo más tarde.

## 2 · APK

1. Crea un repo (p. ej. `github.com/svaronam/oporadar`) y sube **toda** la carpeta `oporadar/` (incluida `.github/`).
2. Actions compila sola la APK en cada push que toque `android/`. Descárgala desde **Releases → «ultima» → OpoRadar.apk** (directamente desde el móvil) o desde el artefacto del workflow.
3. Instálala, abre la app → **Ajustes**: servidor `http://homelab2:8790` → **Guardar** (comprueba la conexión) → **Probar aviso**.

La APK va firmada siempre con la misma clave (guardada en GitHub Secrets, ver «Firma de la APK»), así que las versiones nuevas se instalan encima sin desinstalar.

**Cómo llegan los avisos:** cada 30 min (configurable, mínimo 15) la app pregunta a la Pi por Tailscale si hay algo nuevo desde el último anuncio que vio. Si el móvil está sin Tailscale un rato no se pierde nada: lo recoge en la siguiente consulta. Si entran muchas de golpe, verás un resumen y las 4 mejores.

Para que Android no la duerma: Ajustes del móvil → Apps → OpoRadar → Batería → **Sin restricciones**.

La interfaz de la app es la misma web que sirve la Pi, así que mejoras en el servidor llegan sin recompilar.

## Ajustes útiles (`server/config.json`)

- `vigilar_cada_horas`: cada cuánto se revisan las páginas de tus convocatorias apuntadas (4 por defecto).
- `token`: pon uno si quieres proteger la web/API (la app lo pide en Ajustes).
- `palabras_extra`: más términos que cuenten como informática (p. ej. `"telecomunicaciones"`).
- `notificar.tipos`: añade `"seguimiento"` si también quieres aviso de listas de admitidos, fechas de examen…
- `grupos`: si algún día quieres quitar o añadir grupos.

## Comprobar el clasificador

```bash
cd server && python3 -m unittest discover tests
python3 run.py demo     # mete 5 anuncios de ejemplo para ver la web/app
```

## Firma de la APK

La clave de firma no está en el repositorio. GitHub Actions la recibe de dos secretos del repo (*Settings → Secrets and variables → Actions*):

| Secreto | Contenido |
|---|---|
| `KEYSTORE_BASE64` | el archivo de la clave en Base64 (`base64 -w0 archivo`) |
| `KEYSTORE_PASSWORD` | su contraseña |

Para compilar en local, deja el archivo de la clave en `android/app/keystore/oporadar.jks` (está en `.gitignore`) y define `KEYSTORE_PASSWORD` antes de lanzar Gradle.
