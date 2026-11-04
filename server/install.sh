#!/usr/bin/env bash
# Instala OpoRadar como servicio en la Raspberry (Raspberry Pi OS Lite). Ejecutar desde la carpeta server/:
#   bash install.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
USUARIO="$(whoami)"

echo "== OpoRadar en $DIR (usuario $USUARIO)"
sudo apt-get update -qq
# python3 ya viene en Pi OS; poppler-utils (pdftotext) sirve para leer los anuncios del BOC que vienen en PDF
sudo apt-get install -y -qq python3 poppler-utils sqlite3

[ -f "$DIR/config.json" ] || cp "$DIR/config.example.json" "$DIR/config.json"
mkdir -p "$DIR/data"

sudo tee /etc/systemd/system/oporadar.service >/dev/null <<EOF
[Unit]
Description=OpoRadar - vigilancia de oposiciones de informatica
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
User=$USUARIO
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/run.py servir
Restart=always
RestartSec=15
Environment=PYTHONUNBUFFERED=1
Environment=TZ=Europe/Madrid

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now oporadar
sleep 2
systemctl --no-pager --lines=5 status oporadar || true

IP_TS="$(tailscale ip -4 2>/dev/null | head -1 || true)"
echo
echo "== Listo. Abre en el móvil (con Tailscale activo):"
echo "   http://$(hostname):8790     ó   http://${IP_TS:-<ip-tailscale>}:8790"
echo "== Primera vez, para rellenar el último mes:  python3 $DIR/run.py barrida --dias 30"
echo "== Logs: journalctl -u oporadar -f    ó   tail -f $DIR/data/oporadar.log"
