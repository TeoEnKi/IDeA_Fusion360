"""
Consent Manager - Manages user preferences for AI guidance mode.
Handles first-run consent dialog and persistent settings storage.
"""

import json
import os
from typing import Optional
from enum import Enum


class AIGuidanceMode(Enum):
    """AI guidance behavior modes."""
    ON = "ON"       # Automatically show redirect guidance
    ASK = "ASK"     # Ask before each redirect
    OFF = "OFF"     # Only show a warning, no guided redirect


class ConsentManager:
    """Manages user consent and AI guidance preferences."""

    DEFAULT_PREFERENCES = {
        "ai_guidance_mode": "ASK",
        "first_run_completed": False,
        "show_context_warnings": True
    }

    def __init__(self, user_data_dir: str):
        """
        Initialize the consent manager.

        Args:
            user_data_dir: Path to the user data directory where preferences are stored.
        """
        self.user_data_dir = user_data_dir
        self.preferences_file = os.path.join(user_data_dir, "user_preferences.json")
        self._preferences = None
        self._load_preferences()

    def _ensure_directory(self):
        """Ensure the user data directory exists."""
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir, exist_ok=True)

    def _load_preferences(self):
        """Load preferences from disk or create defaults."""
        self._ensure_directory()

        if os.path.exists(self.preferences_file):
            try:
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    self._preferences = json.load(f)
                # Ensure all default keys exist
                for key, value in self.DEFAULT_PREFERENCES.items():
                    if key not in self._preferences:
                        self._preferences[key] = value
            except (json.JSONDecodeError, IOError):
                self._preferences = self.DEFAULT_PREFERENCES.copy()
        else:
            self._preferences = self.DEFAULT_PREFERENCES.copy()

    def _save_preferences(self):
        """Save preferences to disk."""
        self._ensure_directory()
        try:
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self._preferences, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't write

    def get_guidance_mode(self) -> AIGuidanceMode:
        """Get the current AI guidance mode."""
        mode_str = self._preferences.get("ai_guidance_mode", "ASK")
        try:
            return AIGuidanceMode(mode_str)
        except ValueError:
            return AIGuidanceMode.ASK

    def set_guidance_mode(self, mode: AIGuidanceMode):
        """
        Set the AI guidance mode.

        Args:
            mode: The new guidance mode.
        """
        self._preferences["ai_guidance_mode"] = mode.value
        self._save_preferences()

    def is_first_run(self) -> bool:
        """Check if this is the first run (consent not yet collected)."""
        return not self._preferences.get("first_run_completed", False)

    def mark_first_run_complete(self):
        """Mark first run as complete after user provides consent."""
        self._preferences["first_run_completed"] = True
        self._save_preferences()

    def should_show_context_warnings(self) -> bool:
        """Check if context warnings should be displayed."""
        return self._preferences.get("show_context_warnings", True)

    def set_show_context_warnings(self, show: bool):
        """Set whether to show context warnings."""
        self._preferences["show_context_warnings"] = show
        self._save_preferences()

    def get_all_preferences(self) -> dict:
        """Get all preferences as a dictionary."""
        return self._preferences.copy()

    def reset_preferences(self):
        """Reset all preferences to defaults."""
        self._preferences = self.DEFAULT_PREFERENCES.copy()
        self._save_preferences()

    def should_auto_redirect(self) -> bool:
        """Check if redirects should happen automatically (ON mode)."""
        return self.get_guidance_mode() == AIGuidanceMode.ON

    def should_ask_before_redirect(self) -> bool:
        """Check if we should ask before redirecting (ASK mode)."""
        return self.get_guidance_mode() == AIGuidanceMode.ASK

    def is_redirect_disabled(self) -> bool:
        """Check if redirects are disabled (OFF mode)."""
        return self.get_guidance_mode() == AIGuidanceMode.OFF
