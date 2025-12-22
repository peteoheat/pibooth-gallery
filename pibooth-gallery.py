"""
pibooth-gallery plugin (v1.1.3)

Creates a thumbnail for the final saved picture, updates/merges thumbs.json,
copies gallery_template.html -> gallery.html if configured, and informs other
plugins (e.g. rclone uploader) by setting app attributes.

Requires Pillow (PIL).

Behavior:
- Does NOT add QRCODE settings to pibooth.cfg.
- If a QRCODE section exists in the config, reads keys: save, suffix, ext, save_path.
- Waits briefly for the qrcode file to appear (configurable) before writing manifest.
- If a QR code file is found, adds "qrcode" to the manifest entry.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional

import pibooth
from PIL import Image

__version__ = "1.1.3"

logger = logging.getLogger("pibooth_gallery")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


@pibooth.hookimpl
def pibooth_configure(cfg):
    cfg.add_option('GALLERY', 'GALLERY_ENABLED', 'yes', 'Enable gallery plugin features')

    # Thumbnail settings
    cfg.add_option('GALLERY', 'GALLERY_SIZE', '300x300', 'Thumbnail size WxH')
    cfg.add_option('GALLERY', 'GALLERY_SUFFIX', '_thumb', 'Suffix for thumbnail files')
    cfg.add_option('GALLERY', 'GALLERY_QUALITY', '85', 'JPEG quality for thumbnails')
    cfg.add_option('GALLERY', 'GALLERY_OUTPUT_FOLDER', '', 'Optional subfolder near image to write thumbs')
    cfg.add_option('GALLERY', 'GALLERY_KEEP_ASPECT', 'yes', 'Keep aspect ratio when resizing')

    # Manifest settings
    cfg.add_option('GALLERY', 'GALLERY_UPDATE_MANIFEST', 'yes', 'Update or create thumbs.json after thumbnail creation')
    cfg.add_option('GALLERY', 'GALLERY_MANIFEST_NAME', 'thumbs.json', 'Manifest filename to write/update in image directory')
    cfg.add_option('GALLERY', 'GALLERY_MANIFEST_INCLUDE_BASE_URL', 'yes', 'Include base_url (from GALLERY_BASE_URL or DOWNLOADER) when writing manifest entries')

    # Gallery HTML settings
    cfg.add_option('GALLERY', 'GALLERY_TEMPLATE', '', 'Optional path to gallery_template.html')
    cfg.add_option('GALLERY', 'GALLERY_OUTPUT', 'gallery.html', 'Output filename for gallery HTML')

    # Base URL
    cfg.add_option('GALLERY', 'GALLERY_BASE_URL', '', 'Optional base URL to prefix thumb/full entries and gallery links')

    # Optional small wait for qrcode appearance (seconds). Default 1.0
    cfg.add_option('GALLERY', 'GALLERY_QRCODE_WAIT_SECONDS', '1.0', 'Seconds to wait/poll for qrcode file before writing manifest')


@pibooth.hookimpl
def pibooth_startup(cfg, app):
    app.gallery_enabled = (cfg.get('GALLERY', 'GALLERY_ENABLED') or 'yes').lower() in ('1', 'true', 'yes', 'on')
    app.gallery_size = (cfg.get('GALLERY', 'GALLERY_SIZE') or '300x300')
    app.gallery_suffix = (cfg.get('GALLERY', 'GALLERY_SUFFIX') or '_thumb')
    try:
        app.gallery_quality = int(cfg.get('GALLERY', 'GALLERY_QUALITY') or 85)
    except Exception:
        app.gallery_quality = 85
    app.gallery_output_folder = (cfg.get('GALLERY', 'GALLERY_OUTPUT_FOLDER') or '')
    app.gallery_keep_aspect = (cfg.get('GALLERY', 'GALLERY_KEEP_ASPECT') or 'yes').lower() in ('1', 'true', 'yes', 'on')

    app.gallery_update_manifest = (cfg.get('GALLERY', 'GALLERY_UPDATE_MANIFEST') or 'yes').lower() in ('1', 'true', 'yes', 'on')
    app.gallery_manifest_name = (cfg.get('GALLERY', 'GALLERY_MANIFEST_NAME') or 'thumbs.json')
    app.gallery_manifest_include_base_url = (cfg.get('GALLERY', 'GALLERY_MANIFEST_INCLUDE_BASE_URL') or 'yes').lower() in ('1', 'true', 'yes', 'on')

    app.gallery_template = (cfg.get('GALLERY', 'GALLERY_TEMPLATE') or '')
    app.gallery_output = (cfg.get('GALLERY', 'GALLERY_OUTPUT') or 'gallery.html')

    # Read explicit base URL from GALLERY first, fall back to DOWNLOADER.base_url
    explicit_base = (cfg.get('GALLERY', 'GALLERY_BASE_URL') or '').strip() or None
    if explicit_base:
        app.gallery_base_url = explicit_base
    else:
        try:
            base_url = cfg.get('DOWNLOADER', 'base_url', fallback=None)
            if not base_url:
                base_url = cfg.get('DEFAULT', 'base_url', fallback=None)
        except Exception:
            base_url = None
        app.gallery_base_url = base_url

    # Read qrcode settings only if present; do NOT add them to config
    try:
        q_save_raw = cfg.get('QRCODE', 'save', fallback=None)
        app.qrcode_save = (str(q_save_raw).lower() in ('1', 'true', 'yes', 'on')) if q_save_raw is not None else False
    except Exception:
        app.qrcode_save = False
    try:
        qs = cfg.get('QRCODE', 'suffix', fallback=None)
        app.qrcode_suffix = (qs or '_qrcode')
    except Exception:
        app.qrcode_suffix = '_qrcode'
    try:
        qe = cfg.get('QRCODE', 'ext', fallback=None)
        app.qrcode_ext = (qe or 'png')
        if app.qrcode_ext.startswith('.'):
            app.qrcode_ext = app.qrcode_ext[1:]
    except Exception:
        app.qrcode_ext = 'png'
    try:
        sp = cfg.get('QRCODE', 'save_path', fallback=None)
        app.qrcode_save_path = (sp.strip() or None) if sp is not None else None
    except Exception:
        app.qrcode_save_path = None

    # Read optional qrcode wait timeout (seconds)
    try:
        app.qrcode_wait_seconds = float(cfg.get('GALLERY', 'GALLERY_QRCODE_WAIT_SECONDS', fallback='1.0') or 1.0)
    except Exception:
        app.qrcode_wait_seconds = 1.0

    log = getattr(app, "logger", logger)
    log.info(
        "pibooth-gallery: startup configured (enabled=%s size=%s suffix=%s update_manifest=%s gallery_template=%s base_url=%s qrcode_save=%s qrcode_suffix=%s qrcode_ext=%s qrcode_save_path=%s qrcode_wait=%s)",
        app.gallery_enabled, app.gallery_size, app.gallery_suffix, app.gallery_update_manifest, app.gallery_template, app.gallery_base_url,
        app.qrcode_save, app.qrcode_suffix, app.qrcode_ext, app.qrcode_save_path, app.qrcode_wait_seconds
    )


def _parse_size(size_str: str):
    try:
        w, h = size_str.lower().split('x')
        return int(w), int(h)
    except Exception:
        return 300, 300


def _make_output_path(final_path: Path, suffix: str, output_folder: str) -> Path:
    if output_folder:
        outdir = final_path.parent / output_folder
        outdir.mkdir(parents=True, exist_ok=True)
        return outdir / (final_path.stem + suffix + final_path.suffix)
    return final_path.with_name(final_path.stem + suffix + final_path.suffix)


def _generate_thumbnail_from_file(src_path: Path, dst_path: Path, size, quality: int, keep_aspect: bool):
    with Image.open(src_path) as im:
        if keep_aspect:
            im.thumbnail(size, Image.LANCZOS)
            im.save(dst_path, quality=quality)
        else:
            thumb = im.resize(size, Image.LANCZOS)
            thumb.save(dst_path, quality=quality)


def _load_manifest(manifest_path: Path) -> list:
    try:
        if manifest_path.exists():
            with manifest_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    return data
    except Exception:
        pass
    return []


def _write_manifest_atomic(manifest_path: Path, data: list) -> bool:
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(manifest_path.parent)) as tf:
            json.dump(data, tf, indent=2)
            tmpname = Path(tf.name)
        tmpname.replace(manifest_path)
        return True
    except Exception:
        return False


def _url_join(base: Optional[str], name: str) -> str:
    if not base:
        return name
    return base.rstrip("/") + "/" + name


def _locate_qrcode_for_image(found: Path, app) -> Optional[Path]:
    """
    Attempt to locate the QR code file corresponding to the saved image `found`.
    Strategy:
    - Check common app attributes set by qrcode plugin.
    - If not present, construct expected qrcode filename from image stem + qrcode_suffix + .ext
      and search in: explicit qrcode_save_path, app.output_dir, image directory.
    """
    log = getattr(app, "logger", logger)
    for attr in ('qrcode_file', 'qrcode_saved_file', 'qrcode_filename', 'qrcode_path', 'qrcode'):
        try:
            val = getattr(app, attr, None)
        except Exception:
            val = None
        if val:
            try:
                p = Path(val)
                if p.exists():
                    return p
            except Exception:
                pass

    if not getattr(app, "qrcode_save", False):
        return None

    suffix = getattr(app, "qrcode_suffix", "_qrcode") or "_qrcode"
    ext = getattr(app, "qrcode_ext", "png") or "png"
    expected_filename = found.stem + suffix + "." + ext

    candidate_dirs = []
    try:
        if getattr(app, "qrcode_save_path", None):
            candidate_dirs.append(Path(app.qrcode_save_path))
    except Exception:
        pass

    try:
        outdir = getattr(app, "output_dir", None)
        if outdir:
            candidate_dirs.append(Path(outdir))
    except Exception:
        pass

    candidate_dirs.append(found.parent)

    for d in candidate_dirs:
        try:
            p = d / expected_filename
            if p.exists():
                return p
        except Exception:
            continue

    log.debug("pibooth-gallery: qrcode not found for %s using expected name %s in %s", found, expected_filename, candidate_dirs)
    return None


def _wait_for_qrcode(found: Path, app, timeout: float = 1.0, poll: float = 0.1) -> Optional[Path]:
    """
    Wait briefly for the qrcode file to appear (polling).
    Returns the Path if found within timeout, otherwise None.
    """
    end = time.time() + timeout
    while time.time() < end:
        p = _locate_qrcode_for_image(found, app)
        if p:
            return p
        time.sleep(poll)
    return None


@pibooth.hookimpl(tryfirst=True)
def state_processing_exit(app):
    log = getattr(app, "logger", logger)
    if not getattr(app, "gallery_enabled", True):
        return

    # discover filename from known app attributes
    filename = getattr(app, 'previous_picture_file', None)
    if not filename:
        for attr in ('last_picture', 'last_saved_file', 'picture_file'):
            try:
                val = getattr(app, attr, None)
            except Exception:
                val = None
            if val:
                filename = val
                break
    if not filename:
        log.debug("pibooth-gallery: no filename found; skipping")
        return

    found = Path(filename)
    if not found.exists():
        log.debug("pibooth-gallery: file not found %s; skipping", found)
        return

    size = _parse_size(app.gallery_size)
    thumb_path = _make_output_path(found, app.gallery_suffix, app.gallery_output_folder)

    try:
        _generate_thumbnail_from_file(found, thumb_path, size, app.gallery_quality, app.gallery_keep_aspect)
        log.info("pibooth-gallery: thumbnail created %s", thumb_path)
    except Exception as exc:
        log.exception("pibooth-gallery: failed to create thumbnail: %s", exc)
        return

    # Inform other plugins with several common attributes
    try:
        setattr(app, "previous_picture_file", str(found))
        setattr(app, "previous_thumbnail_file", str(thumb_path))
        try:
            prev_list = getattr(app, "previous_picture_files", None)
            if isinstance(prev_list, list):
                prev_list.insert(0, str(found))
            else:
                setattr(app, "previous_picture_files", [str(found)])
        except Exception:
            setattr(app, "previous_picture_files", [str(found)])
        log.debug("pibooth-gallery: set app previous file attributes")
    except Exception:
        log.exception("pibooth-gallery: unable to set app previous file attributes")

    # locate qrcode (if any) with a short wait to avoid race conditions
    qrcode_path = _wait_for_qrcode(found, app, timeout=getattr(app, "qrcode_wait_seconds", 1.0), poll=0.1)

    # Update/merge manifest (thumbs.json)
    if app.gallery_update_manifest:
        manifest_path = found.parent / app.gallery_manifest_name
        try:
            try:
                thumb_rel = str(thumb_path.relative_to(found.parent))
            except Exception:
                thumb_rel = thumb_path.name
            full_rel = found.name

            base_url = app.gallery_base_url if app.gallery_manifest_include_base_url else None
            thumb_url = _url_join(base_url, thumb_rel) if base_url else thumb_rel
            full_url = _url_join(base_url, full_rel) if base_url else full_rel

            qrcode_url = None
            if qrcode_path:
                try:
                    qrcode_rel = str(qrcode_path.relative_to(found.parent))
                except Exception:
                    qrcode_rel = qrcode_path.name
                qrcode_url = _url_join(base_url, qrcode_rel) if base_url else qrcode_rel

            manifest = _load_manifest(manifest_path)
            manifest = [e for e in manifest if e.get("filename") != full_rel and e.get("full") != full_url]

            new_entry = {"thumb": thumb_url, "full": full_url, "filename": full_rel}
            if qrcode_url:
                new_entry["qrcode"] = qrcode_url

            manifest.insert(0, new_entry)

            success = _write_manifest_atomic(manifest_path, manifest)
            if success:
                log.info("pibooth-gallery: manifest updated %s (entries=%d)", manifest_path, len(manifest))
            else:
                log.warning("pibooth-gallery: failed to write manifest %s", manifest_path)
        except Exception:
            log.exception("pibooth-gallery: manifest update failed for %s", found)

    # Copy gallery template to output file (gallery.html)
    tpl_path = Path(app.gallery_template) if app.gallery_template else None
    if tpl_path and tpl_path.is_file():
        gallery_path = found.parent / app.gallery_output
        try:
            with tpl_path.open("r", encoding="utf-8") as tf:
                tpl = tf.read()
            with gallery_path.open("w", encoding="utf-8") as gf:
                gf.write(tpl)
            log.info("pibooth-gallery: gallery.html written %s -> %s", tpl_path, gallery_path)
        except Exception:
            log.exception("pibooth-gallery: failed to copy gallery template %s", tpl_path)


@pibooth.hookimpl
def pibooth_cleanup(app):
    log = getattr(app, "logger", logger)
    log.debug("pibooth-gallery: pibooth_cleanup called")
