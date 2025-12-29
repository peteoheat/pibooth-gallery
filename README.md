pibooth-gallery
========================

A plugin for `pibooth <https://github.com/pibooth/pibooth>`_ that automatically
creates thumbnails, maintains a gallery manifest (``thumbs.json``), and optionally
generates a static HTML gallery page for each event.  
It is designed to integrate cleanly with other plugins such as uploaders
(e.g., rclone-based sync modules) and optional QR code generators.

This plugin requires **Pillow (PIL)**.

Features
--------

* Automatically generates a thumbnail for every final saved picture.
* Configurable thumbnail size, quality, suffix, and output folder.
* Creates or updates a ``thumbs.json`` manifest containing:
  
  - Thumbnail path or URL  
  - Full-size image path or URL  
  - Optional QR code path or URL  

* Supports optional ``gallery_template.html`` → ``gallery.html`` generation.
* Integrates with QR code plugins without modifying ``pibooth.cfg``.
* Provides attributes to other plugins:

  - ``previous_picture_file``  
  - ``previous_thumbnail_file``  
  - ``previous_picture_files`` (list)

* Robust handling of race conditions when QR codes are generated asynchronously.
* Atomic writes for manifest updates to avoid corruption.

Installation
------------

Install via pip:

.. code-block:: bash

    pip install pibooth-gallery

Or clone into your pibooth plugins directory:

.. code-block:: bash

    git clone https://github.com/peteoheat/pibooth-gallery.git

Configuration
-------------

All configuration options live under the ``[GALLERY]`` section of ``pibooth.cfg``.

Example:

.. code-block:: ini

    [GALLERY]
    GALLERY_ENABLED = yes
    GALLERY_SIZE = 300x300
    GALLERY_SUFFIX = _thumb
    GALLERY_QUALITY = 85
    GALLERY_OUTPUT_FOLDER =
    GALLERY_KEEP_ASPECT = yes

    GALLERY_UPDATE_MANIFEST = yes
    GALLERY_MANIFEST_NAME = thumbs.json
    GALLERY_MANIFEST_INCLUDE_BASE_URL = yes

    GALLERY_TEMPLATE = /home/pi/gallery_template.html
    GALLERY_OUTPUT = gallery.html

    GALLERY_BASE_URL = https://example.com/event123/
    GALLERY_QRCODE_WAIT_SECONDS = 1.0

Configuration Options
---------------------

Thumbnail Options
~~~~~~~~~~~~~~~~~

``GALLERY_ENABLED``  
    Enable or disable the plugin. Default: ``yes``

``GALLERY_SIZE``  
    Thumbnail size in ``WxH`` format. Default: ``300x300``

``GALLERY_SUFFIX``  
    Suffix appended to thumbnail filenames. Default: ``_thumb``

``GALLERY_QUALITY``  
    JPEG quality (1–100). Default: ``85``

``GALLERY_OUTPUT_FOLDER``  
    Optional subfolder for thumbnails relative to the image directory.

``GALLERY_KEEP_ASPECT``  
    Preserve aspect ratio when resizing. Default: ``yes``

Manifest Options
~~~~~~~~~~~~~~~~

``GALLERY_UPDATE_MANIFEST``  
    Enable writing/updating ``thumbs.json``. Default: ``yes``

``GALLERY_MANIFEST_NAME``  
    Filename for the manifest. Default: ``thumbs.json``

``GALLERY_MANIFEST_INCLUDE_BASE_URL``  
    Prefix entries with ``GALLERY_BASE_URL`` (or DOWNLOADER.base_url). Default: ``yes``

Gallery HTML Options
~~~~~~~~~~~~~~~~~~~~

``GALLERY_TEMPLATE``  
    Optional path to ``gallery_template.html``

``GALLERY_OUTPUT``  
    Output filename (written next to images). Default: ``gallery.html``

Base URL
~~~~~~~~

``GALLERY_BASE_URL``  
    Optional base URL for manifest entries and gallery links.  
    Falls back to ``DOWNLOADER.base_url`` if not set.

QR Code Integration
~~~~~~~~~~~~~~~~~~~

The plugin **does not add or modify** any ``[QRCODE]`` settings.

If a QR code plugin is installed and configured, pibooth-gallery will:

* Detect QR code files using common attributes (``qrcode_file``, ``qrcode_path``…)
* Or construct the expected filename using:

  - ``suffix`` (default: ``_qrcode``)  
  - ``ext`` (default: ``png``)  
  - ``save_path`` (if provided)

* Wait briefly (configurable) for the QR code file to appear.

Workflow
--------

1. User finishes a photo session.
2. pibooth saves the final composite image.
3. pibooth-gallery:

   * Locates the saved image.
   * Generates a thumbnail.
   * Updates ``previous_*`` attributes for other plugins.
   * Waits briefly for a QR code file (if enabled).
   * Updates or creates ``thumbs.json``.
   * Optionally writes ``gallery.html`` from a template.

4. Other plugins (e.g., uploaders) can immediately use:

   * ``previous_picture_file``
   * ``previous_thumbnail_file``
   * ``previous_picture_files``

Manifest Format
---------------

Example ``thumbs.json`` entry:

.. code-block:: json

    {
      "thumb": "thumbs/IMG_001_thumb.jpg",
      "full": "IMG_001.jpg",
      "filename": "IMG_001.jpg",
      "qrcode": "IMG_001_qrcode.png"
    }

If ``GALLERY_MANIFEST_INCLUDE_BASE_URL = yes``:

.. code-block:: json

    {
      "thumb": "https://example.com/event/thumbs/IMG_001_thumb.jpg",
      "full": "https://example.com/event/IMG_001.jpg",
      "filename": "IMG_001.jpg"
    }

Integration With Uploaders
--------------------------

The plugin is designed to work seamlessly with uploaders such as:

* rclone-based sync plugins
* S3/Cloudflare Workers uploaders
* Custom automation scripts

Because the plugin sets ``previous_*`` attributes early, uploaders can:

* Upload the full image
* Upload the thumbnail
* Upload the QR code (if present)
* Upload the manifest
* Upload the gallery HTML

Version
-------

Current version: **1.1.3**

License
-------

MIT License. See ``LICENSE`` for details.

Contributing
------------

Pull requests are welcome.  
Please open an issue for feature requests or bug reports.

``pibooth-gallery`` is maintained by the community and designed for event
photography workflows that require automation, reliability, and clean integration
with cloud uploaders and gallery systems.
