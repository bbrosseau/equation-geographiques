#!/usr/bin/env bash
# Paquet .deb (Debian, Ubuntu, Linux de ChromeOS) à partir de dist/Mireille-Tuto produit par PyInstaller.
# Usage : packaging/linux/build-deb.sh 1.0.0
set -euo pipefail

VERSION="${1:?usage: build-deb.sh VERSION}"
ROOT="build/deb/mireille-tuto"

rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" "$ROOT/opt" "$ROOT/usr/bin" \
         "$ROOT/usr/share/applications" "$ROOT/usr/share/icons/hicolor/256x256/apps"

cp -r dist/Mireille-Tuto "$ROOT/opt/mireille-tuto"
ln -s /opt/mireille-tuto/Mireille-Tuto "$ROOT/usr/bin/mireille-tuto"
cp src/mireille_tuto/data/icon.png "$ROOT/usr/share/icons/hicolor/256x256/apps/mireille-tuto.png"

cat > "$ROOT/usr/share/applications/mireille-tuto.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Mireille Tuto
Comment=Apprendre l'algèbre et l'apprentissage machine sur une carte du monde
Exec=/opt/mireille-tuto/Mireille-Tuto
Icon=mireille-tuto
Categories=Education;Math;
Terminal=false
EOF

# Bibliothèques système dont Qt a besoin (non incluses dans les roues PySide6).
cat > "$ROOT/DEBIAN/control" <<EOF
Package: mireille-tuto
Version: $VERSION
Section: education
Priority: optional
Architecture: amd64
Maintainer: Bernard Brosseau-Villeneuve <bbrosseau@gmail.com>
Depends: libgl1, libegl1, libfontconfig1, libdbus-1-3, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0
Description: Mireille Tuto
 Application interactive pour apprendre l'algèbre et l'apprentissage machine
 à partir d'une carte du monde.
EOF

dpkg-deb --build --root-owner-group "$ROOT" dist/Mireille-Tuto-Linux.deb
