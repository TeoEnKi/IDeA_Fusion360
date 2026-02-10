"""
Asset Manager - Converts images and resources to data URLs for the palette.
Eliminates need for Flask/HTTP server to serve assets.
"""

import base64
import os
from typing import Optional, Dict


# MIME types for common image formats
MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webp": "image/webp"
}


def file_to_data_url(file_path: str) -> Optional[str]:
    """Convert a file to a base64 data URL."""
    if not os.path.exists(file_path):
        return None

    ext = os.path.splitext(file_path)[1].lower()
    mime_type = MIME_TYPES.get(ext, "application/octet-stream")

    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        encoded = base64.b64encode(data).decode('utf-8')
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return None


def get_cursor_sprite(assets_dir: str) -> Optional[str]:
    """Get the cursor sprite image as a data URL."""
    cursor_path = os.path.join(assets_dir, "cursor.png")
    return file_to_data_url(cursor_path)


def get_icon(assets_dir: str, icon_name: str) -> Optional[str]:
    """Get an icon image as a data URL."""
    icon_path = os.path.join(assets_dir, "icons", icon_name)
    return file_to_data_url(icon_path)


class AssetManager:
    """Manages loading and caching of assets as data URLs."""

    # Redirect image filenames
    REDIRECT_IMAGES = {
        "fusion_design_tabs.png": "Design workspace tabs (SOLID/SURFACE/SHEET METAL)",
        "fusion_workspace_selector.png": "Workspace dropdown selector",
        "fusion_sketch_mode.png": "Sketch mode entry",
        "fusion_form_mode.png": "Form (T-Spline) mode",
        "fusion_new_design.png": "New design creation",
        "fusion_finish_sketch.png": "Finish sketch button"
    }

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.assets_dir = os.path.join(base_dir, "assets")
        self._cache: Dict[str, str] = {}

    def get_asset(self, relative_path: str, use_cache: bool = True) -> Optional[str]:
        """Get an asset as a data URL."""
        if use_cache and relative_path in self._cache:
            return self._cache[relative_path]

        full_path = os.path.join(self.assets_dir, relative_path)
        data_url = file_to_data_url(full_path)

        if data_url and use_cache:
            self._cache[relative_path] = data_url

        return data_url

    def get_cursor_sprite(self) -> Optional[str]:
        """Get the cursor sprite for animations."""
        return self.get_asset("cursor.png")

    def preload_assets(self) -> Dict[str, str]:
        """Preload common assets and return as a dictionary."""
        assets = {}

        # Load cursor sprite
        cursor = self.get_cursor_sprite()
        if cursor:
            assets["cursor"] = cursor

        # Load any icons in the icons directory
        icons_dir = os.path.join(self.assets_dir, "icons")
        if os.path.exists(icons_dir):
            for filename in os.listdir(icons_dir):
                ext = os.path.splitext(filename)[1].lower()
                if ext in MIME_TYPES:
                    icon_url = self.get_asset(f"icons/{filename}")
                    if icon_url:
                        name = os.path.splitext(filename)[0]
                        assets[f"icon_{name}"] = icon_url

        # Load redirect images
        redirect_assets = self.preload_redirect_images()
        assets.update(redirect_assets)

        return assets

    def get_redirect_image(self, image_name: str) -> Optional[str]:
        """
        Get a redirect reference image as a data URL.

        Args:
            image_name: The filename of the redirect image (e.g., "fusion_design_tabs.png")

        Returns:
            Data URL string, or None if not found.
        """
        return self.get_asset(f"redirect/{image_name}")

    def preload_redirect_images(self) -> Dict[str, str]:
        """Preload all redirect images and return as a dictionary."""
        redirect_assets = {}

        redirect_dir = os.path.join(self.assets_dir, "redirect")
        if os.path.exists(redirect_dir):
            for filename in self.REDIRECT_IMAGES.keys():
                image_url = self.get_asset(f"redirect/{filename}")
                if image_url:
                    # Key without extension for easier lookup
                    name = os.path.splitext(filename)[0]
                    redirect_assets[f"redirect_{name}"] = image_url

        return redirect_assets

    def clear_cache(self):
        """Clear the asset cache."""
        self._cache.clear()
