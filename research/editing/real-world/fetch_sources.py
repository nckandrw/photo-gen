"""Acquire the G2 real-world source photographs from Wikimedia Commons, with full provenance.

For each selected file it:
  - queries the Commons API (imageinfo: url, size, mime, sha1, timestamp, uploader, extmetadata licence/author/credit,
    commonmetadata EXIF);
  - accepts only CC0 or public-domain licences (LicenseShortName), JPEG/PNG/WebP, <= 50 MB, <= 40 MP, <= 8192 px/side
    (the photo-gen input limits, so nothing is resized);
  - downloads the ORIGINAL file into its own new, empty directory data/benchmark/real-world/originals/<id>/ (gitignored;
    an existing directory is never overwritten), verifies Commons' SHA-1, computes the file SHA-256;
  - decodes it with PIL (untrusted data) to record format, dimensions, EXIF orientation, camera make/model, capture
    date and the embedded ICC profile description, then stages it through photo-gen's own input staging
    (photogen.inputs.stage_input_image) to obtain the canonical pixel SHA-256 and staged path that edits will use.
Writes research/editing/real-world/source-manifest.json. Images are never committed.

Usage: mflux/.venv/bin/python3.12 -I research/editing/real-world/fetch_sources.py <selection.json> [--restage <note>]"""
import hashlib
import html
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app"))
from PIL import Image, ImageCms  # noqa: E402

from photogen.config import AppConfig  # noqa: E402
from photogen.errors import ValidationError  # noqa: E402
from photogen.inputs import stage_input_image  # noqa: E402

UA = "photo-gen-research/0.1 (local benchmark curation; https://github.com/nckandrw)"
API = "https://commons.wikimedia.org/w/api.php"
ORIG = ROOT / "data" / "benchmark" / "real-world" / "originals"
ALLOWED_LICENCES = ("CC0", "Public domain")


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(3 + 5 * attempt)


def text(v):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", v or ""))).strip() or None


def restage(manifest_path: Path, cfg, note: str) -> None:
    """Stage sources whose staging was rejected at acquisition, from the already-downloaded file (verified against
    its recorded sha256 first; never re-downloaded). The original staging_error is kept as history."""
    manifest = json.loads(manifest_path.read_text())
    for sid, e in manifest["sources"].items():
        if e.get("staged"):
            continue
        f = ROOT / e["local_path"]
        if hashlib.sha256(f.read_bytes()).hexdigest() != e["file_sha256"]:
            raise SystemExit(f"{sid}: local file no longer matches its recorded sha256")
        staged, warnings = stage_input_image(str(f), cfg.inputs_dir)
        e["staged"] = {"pixel_sha256": staged.pixel_sha256, "staged_path": staged.staged_path,
                       "width": staged.width, "height": staged.height, "orientation": "portrait"
                       if staged.height > staged.width else "landscape", "warnings": warnings}
        e["restaged"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "note": note}
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
        print(sid, "restaged", staged.source_format, staged.width, staged.height, staged.pixel_sha256[:16], warnings)


def main(selection_path: str) -> None:
    sel = json.loads(Path(selection_path).read_text())
    cfg = AppConfig.load()
    manifest_path = Path(__file__).with_name("source-manifest.json")
    if "--restage" in sys.argv:
        return restage(manifest_path, cfg, sys.argv[sys.argv.index("--restage") + 1])
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"sources": {}}
    for item in sel["sources"]:
        sid, title = item["id"], item["title"]
        if sid in manifest["sources"]:
            print(sid, "already acquired; skipped")
            continue
        q = {"action": "query", "format": "json", "titles": title, "prop": "imageinfo",
             "iiprop": "url|size|mime|sha1|timestamp|user|extmetadata|commonmetadata"}
        page = next(iter(get(API + "?" + urllib.parse.urlencode(q))["query"]["pages"].values()))
        ii = page["imageinfo"][0]
        em = {k: v.get("value") for k, v in (ii.get("extmetadata") or {}).items()}
        cm = {m["name"]: m["value"] for m in (ii.get("commonmetadata") or [])
              if isinstance(m.get("value"), (str, int, float))}
        lic = em.get("LicenseShortName")
        problems = []
        if lic not in ALLOWED_LICENCES:
            problems.append(f"licence {lic!r} not CC0/PD")
        if ii["mime"] not in ("image/jpeg", "image/png", "image/webp"):
            problems.append(f"mime {ii['mime']}")
        if ii["size"] > 50 * 1024 * 1024 or ii["width"] * ii["height"] > 40_000_000 or max(ii["width"], ii["height"]) > 8192:
            problems.append("exceeds photo-gen input limits")
        if problems:
            print(sid, "REJECTED:", problems)
            continue
        d = ORIG / sid
        d.mkdir(parents=True, exist_ok=False)  # its own new, empty directory
        name = urllib.parse.unquote(urllib.parse.urlsplit(ii["url"]).path.rsplit("/", 1)[1])  # no ?utm_ query
        data = get(ii["url"], binary=True)
        sha1 = hashlib.sha1(data).hexdigest()
        if sha1 != ii["sha1"]:
            raise SystemExit(f"{sid}: SHA-1 mismatch (Commons {ii['sha1']}, downloaded {sha1})")
        f = d / name
        f.write_bytes(data)
        with Image.open(io.BytesIO(data)) as im:
            exif = im.getexif()
            icc = im.info.get("icc_profile")
            icc_desc = None
            if icc:
                try:
                    icc_desc = ImageCms.ImageCmsProfile(io.BytesIO(icc)).profile.profile_description
                except Exception as e:  # noqa: BLE001
                    icc_desc = f"(unparsed: {type(e).__name__})"
            info = {"format": im.format, "mode": im.mode, "width": im.width, "height": im.height,
                    "exif_orientation": exif.get(0x0112), "exif_make": exif.get(0x010F), "exif_model": exif.get(0x0110),
                    "exif_datetime": exif.get(0x0132), "icc_profile": icc_desc}
        try:
            staged, warnings = stage_input_image(str(f), cfg.inputs_dir)
        except ValidationError as e:  # recorded, not hidden: a real camera file photo-gen rejects is a finding
            staged, warnings = None, [f"staging rejected: {e}"]
            print(sid, "STAGING REJECTED:", e)
        manifest["sources"][sid] = {
            "id": sid, "category": item["category"],
            "source": "Wikimedia Commons", "title": title, "page_url": ii.get("descriptionurl"),
            "file_url": ii["url"], "commons_pageid": page["pageid"], "uploaded": ii.get("timestamp"),
            "uploader": ii.get("user"),
            "licence": lic, "licence_url": em.get("LicenseUrl"), "usage_terms": text(em.get("UsageTerms")),
            "creator": text(em.get("Artist")), "credit": text(em.get("Credit")),
            "attribution_required": em.get("AttributionRequired"),
            "description": (text(em.get("ImageDescription")) or "")[:300],
            "date_original": text(em.get("DateTimeOriginal")),
            "original_filename": name, "local_path": str(f.relative_to(ROOT)),
            "file_bytes": len(data), "file_sha1_commons": ii["sha1"], "file_sha256": hashlib.sha256(data).hexdigest(),
            "camera_make": info["exif_make"] or cm.get("Make"), "camera_model": info["exif_model"] or cm.get("Model"),
            **{k: info[k] for k in ("format", "mode", "width", "height", "exif_orientation", "icc_profile")},
            "staged": {"pixel_sha256": staged.pixel_sha256, "staged_path": staged.staged_path,
                       "width": staged.width, "height": staged.height, "orientation": "portrait"
                       if staged.height > staged.width else "landscape", "warnings": warnings} if staged else None,
            "staging_error": None if staged else warnings[0],
            "retrieved": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "notes": item.get("notes"),
        }
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
        print(sid, name[:60], info["format"], info["width"], info["height"], lic, info["exif_make"],
              info["exif_model"], "icc:", icc_desc, "orient:", info["exif_orientation"],
              "staged", (staged.width, staged.height) if staged else None)
        time.sleep(1)


if __name__ == "__main__":
    main(sys.argv[1])
