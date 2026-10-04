"""Télécharge les frontières des pays depuis Natural Earth et les installe dans le projet.

    uv run python scripts/update_maps.py              # dernière version (branche master)
    uv run python scripts/update_maps.py --ref v5.1.2 # version figée (tag GitHub)

Les fichiers sont validés avant de remplacer ceux du projet ; la source exacte
(référence, commit, version) est enregistrée dans data/SOURCE.json.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from equation_geographique.geo.countries import DATA_DIR, CountryAtlas

REPO = "nvkelso/natural-earth-vector"
SCALES = ("50m", "110m")
REQUIRED_PROPERTIES = ("ADM0_A3", "NAME", "NAME_FR", "CONTINENT", "POP_EST", "MAPCOLOR7")
MIN_COUNTRIES = 150
SANITY_CHECKS = [(-73.57, 45.50, "CAN"), (2.35, 48.86, "FRA"), (139.69, 35.69, "JPN")]


def filename(scale: str) -> str:
    return f"ne_{scale}_admin_0_countries.geojson"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "equation-geographique"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def resolve_commit(ref: str) -> str:
    data = json.loads(fetch(f"https://api.github.com/repos/{REPO}/commits/{ref}"))
    return data["sha"]


def validate(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        features = json.load(f)["features"]
    for feature in features:
        missing = [p for p in REQUIRED_PROPERTIES if p not in feature["properties"]]
        if missing:
            name = feature["properties"].get("NAME", "?")
            raise ValueError(f"{path.name} : propriétés manquantes pour {name} : {missing}")
    if len(features) < MIN_COUNTRIES:
        raise ValueError(f"{path.name} : seulement {len(features)} pays")

    atlas = CountryAtlas.load(path)
    for lon, lat, code in SANITY_CHECKS:
        country = atlas.country_at(lon, lat)
        if country is None or country.code != code:
            raise ValueError(f"{path.name} : ({lon}, {lat}) devrait être dans {code}, trouvé {country}")
    return len(atlas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ref", default="master", help="branche, tag ou commit du dépôt Natural Earth")
    args = parser.parse_args()

    commit = resolve_commit(args.ref)
    version = fetch(f"https://raw.githubusercontent.com/{REPO}/{commit}/VERSION").decode().strip()
    print(f"Natural Earth {version} — {args.ref} ({commit[:10]})")

    with tempfile.TemporaryDirectory() as tmp:
        downloaded: dict[str, Path] = {}
        counts: dict[str, int] = {}
        for scale in SCALES:
            name = filename(scale)
            print(f"  téléchargement de {name}…")
            target = Path(tmp) / name
            target.write_bytes(fetch(f"https://raw.githubusercontent.com/{REPO}/{commit}/geojson/{name}"))
            counts[scale] = validate(target)
            downloaded[scale] = target
            print(f"    {counts[scale]} pays, {target.stat().st_size / 1e6:.1f} Mo, validé")

        for scale, path in downloaded.items():
            shutil.move(path, DATA_DIR / filename(scale))

    source = {
        "dataset": "Natural Earth — Admin 0 Countries",
        "repository": f"https://github.com/{REPO}",
        "ref": args.ref,
        "commit": commit,
        "version": version,
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": {filename(s): {"scale": f"1:{s}", "countries": counts[s]} for s in SCALES},
    }
    (DATA_DIR / "SOURCE.json").write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Données installées dans {DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
