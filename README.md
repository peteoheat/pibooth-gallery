# pibooth-gallery
PiBooth Gallery is a module created for pibooth to create a web gallery with thumbnails of the images created on the booth
it works alongside pibooth-qrcode which creates the QR code that can be used to download the image, 
but also provides a simple download button and a share button to enable sharing via whatsapp etc on a mobile device.

Configuration
-------------

    [GALLERY]
    # Enable gallery plugin features
    # Required by 'gallery' plugin
    GALLERY_ENABLED = yes

    # Thumbnail size WxH
    # Required by 'gallery' plugin
    GALLERY_SIZE = 300x300

    # Suffix for thumbnail files
    # Required by 'gallery' plugin
    GALLERY_SUFFIX = _thumb

    # JPEG quality for thumbnails
    # Required by 'gallery' plugin
    GALLERY_QUALITY = 85

    # Optional subfolder near image to write thumbs
    # Required by 'gallery' plugin
    GALLERY_OUTPUT_FOLDER = 

    # Keep aspect ratio when resizing
    # Required by 'gallery' plugin
    GALLERY_KEEP_ASPECT = yes

    # Update or create thumbs.json after thumbnail creation
    # Required by 'gallery' plugin
    GALLERY_UPDATE_MANIFEST = yes

    # Manifest filename to write/update in image directory
    # Required by 'gallery' plugin
    GALLERY_MANIFEST_NAME = thumbs.json

    # Include base_url (from GALLERY_BASE_URL or DOWNLOADER) when writing manifest entries
    # Required by 'gallery' plugin
    GALLERY_MANIFEST_INCLUDE_BASE_URL = yes

    # Optional path to gallery_template.html
    # Required by 'gallery' plugin
    GALLERY_TEMPLATE = /home/pi/.config/pibooth/gallery_templates/seasonal_snowflake_gallery_template_with_QR_carousel.html

    # Output filename for gallery HTML
    # Required by 'gallery' plugin
    GALLERY_OUTPUT = gallery.html

    # Optional base URL to prefix thumb/full entries and gallery links
    # Required by 'gallery' plugin
    GALLERY_BASE_URL = https://MYPICTUREWEBSITE.COM/MYGALLERYSUBFOLDER/

    # Seconds to wait/poll for qrcode file before writing manifest
    # Required by 'gallery' plugin
    GALLERY_QRCODE_WAIT_SECONDS = 3
