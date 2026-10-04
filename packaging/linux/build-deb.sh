#!/usr/bin/env bash
# Paquet .deb (Debian, Ubuntu, Linux de ChromeOS) à partir de dist/Equation-Geographique produit par PyInstaller.
# Usage : packaging/linux/build-deb.sh 1.0.0
set -euo pipefail

VERSION="${1:?usage: build-deb.sh VERSION}"
ROOT="build/deb/equation-geographique"

rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" "$ROOT/opt" "$ROOT/usr/bin" \
         "$ROOT/usr/share/applications" "$ROOT/usr/share/icons/hicolor/256x256/apps"

cp -r dist/Equation-Geographique "$ROOT/opt/equation-geographique"
ln -s /opt/equation-geographique/Equation-Geographique "$ROOT/usr/bin/equation-geographique"
cp src/equation_geographique/data/icon.png "$ROOT/usr/share/icons/hicolor/256x256/apps/equation-geographique.png"

cat > "$ROOT/usr/share/applications/equation-geographique.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Équation géographique
Comment=Apprendre l'algèbre et l'apprentissage machine sur une carte du monde
Exec=/opt/equation-geographique/Equation-Geographique
Icon=equation-geographique
Categories=Education;Math;
Terminal=false
EOF

# Bibliothèques système dont Qt a besoin (non incluses dans les roues PySide6).
cat > "$ROOT/DEBIAN/control" <<EOF
Package: equation-geographique
Version: $VERSION
Section: education
Priority: optional
Architecture: amd64
Maintainer: Bernard Brosseau-Villeneuve <bbrosseau@gmail.com>
Depends: libgl1, libegl1, libfontconfig1, libdbus-1-3, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0
Description: Équation géographique
 Application interactive pour apprendre l'algèbre et l'apprentissage machine
 à partir d'une carte du monde.
EOF

dpkg-deb --build --root-owner-group "$ROOT" dist/Equation-Geographique-Linux.deb
