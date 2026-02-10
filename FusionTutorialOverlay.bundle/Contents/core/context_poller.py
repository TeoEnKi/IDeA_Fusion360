"""
Context Poller - Monitors Fusion 360 context changes during redirect mode.
Polls at intervals to detect when the user has navigated to the correct context.
"""

from typing import Dict, Any, Callable, Optional
import threading
import time

try:
    import adsk.core
    FUSION_AVAILABLE = True
except ImportError:
    FUSION_AVAILABLE = False

try:
    from .context_detector import FusionContextDetector
except ImportError:
    # Fallback for direct execution
    from context_detector import FusionContextDetector


class ContextPollingManager:
    """Manages polling for context changes during redirect mode."""

    # Default poll interval in seconds
    DEFAULT_POLL_INTERVAL = 0.5  # 500ms

    def __init__(self, context_detector: FusionContextDetector = None):
        """
        Initialize the polling manager.

        Args:
            context_detector: The context detector instance to use.
        """
        self.context_detector = context_detector or FusionContextDetector()
        self._polling = False
        self._poll_thread = None
        self._required_context: Dict[str, Any] = {}
        self._on_context_matched: Optional[Callable] = None
        self._on_poll_tick: Optional[Callable] = None
        self._poll_interval = self.DEFAULT_POLL_INTERVAL
        self._custom_event = None
        self._app = None

        if FUSION_AVAILABLE:
            try:
                self._app = adsk.core.Application.get()
            except:
                pass

    def start_polling(
        self,
        required: Dict[str, Any],
        on_matched: Callable[[Dict[str, Any]], None],
        on_tick: Callable[[Dict[str, Any]], None] = None,
        interval_ms: int = None
    ):
        """
        Start polling for context changes.

        Args:
            required: The required context dictionary (workspace, environment, etc.)
            on_matched: Callback fired when context matches requirements.
            on_tick: Optional callback fired on each poll tick with current context.
            interval_ms: Optional poll interval in milliseconds.
        """
        if self._polling:
            self.stop_polling()

        self._required_context = required
        self._on_context_matched = on_matched
        self._on_poll_tick = on_tick

        if interval_ms:
            self._poll_interval = interval_ms / 1000.0

        self._polling = True

        if FUSION_AVAILABLE and self._app:
            # Use Fusion's custom event system for thread-safe callbacks
            self._start_fusion_polling()
        else:
            # Fallback to threading for testing without Fusion
            self._start_thread_polling()

    def stop_polling(self):
        """Stop polling for context changes."""
        self._polling = False

        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)
            self._poll_thread = None

        if self._custom_event:
            try:
                self._app.unregisterCustomEvent(self._custom_event.eventId)
            except:
                pass
            self._custom_event = None

        self._required_context = {}
        self._on_context_matched = None
        self._on_poll_tick = None

    def _start_fusion_polling(self):
        """Start polling using Fusion's event system."""
        try:
            # Create a custom event for context checking
            event_id = 'ContextPollerEvent'

            # Start a background thread that fires the custom event
            self._poll_thread = threading.Thread(target=self._fusion_poll_loop)
            self._poll_thread.daemon = True
            self._poll_thread.start()

        except Exception as e:
            print(f"Error starting Fusion polling: {e}")
            # Fallback to thread polling
            self._start_thread_polling()

    def _fusion_poll_loop(self):
        """Background thread that checks context at intervals."""
        while self._polling:
            try:
                # Check context on the main thread would be ideal,
                # but we can check it here and fire callback
                self._check_context()
            except Exception as e:
                print(f"Polling error: {e}")

            time.sleep(self._poll_interval)

    def _start_thread_polling(self):
        """Start polling using a background thread (for testing)."""
        self._poll_thread = threading.Thread(target=self._thread_poll_loop)
        self._poll_thread.daemon = True
        self._poll_thread.start()

    def _thread_poll_loop(self):
        """Thread-based polling loop."""
        while self._polling:
            self._check_context()
            time.sleep(self._poll_interval)

    def _check_context(self):
        """Check current context against requirements."""
        if not self._polling:
            return

        try:
            current_context = self.context_detector.get_current_context()
            context_dict = current_context.to_dict()

            # Fire tick callback if set
            if self._on_poll_tick:
                try:
                    self._on_poll_tick(context_dict)
                except Exception as e:
                    print(f"Poll tick callback error: {e}")

            # Check if context matches requirements
            if self.context_detector.matches_requirements(self._required_context):
                self._polling = False

                if self._on_context_matched:
                    try:
                        self._on_context_matched(context_dict)
                    except Exception as e:
                        print(f"Context matched callback error: {e}")

        except Exception as e:
            print(f"Context check error: {e}")

    @property
    def is_polling(self) -> bool:
        """Check if currently polling."""
        return self._polling

    def get_current_context(self) -> Dict[str, Any]:
        """Get the current context without affecting polling state."""
        return self.context_detector.get_current_context().to_dict()

    def check_once(self, required: Dict[str, Any]) -> bool:
        """
        Check context once without starting continuous polling.

        Args:
            required: The required context dictionary.

        Returns:
            True if context matches, False otherwise.
        """
        return self.context_detector.matches_requirements(required)


class FusionEventPollingHandler:
    """
    Alternative polling implementation using Fusion's document events.
    More efficient than continuous polling as it responds to actual changes.
    """

    def __init__(self, context_detector: FusionContextDetector = None):
        self.context_detector = context_detector or FusionContextDetector()
        self._required_context: Dict[str, Any] = {}
        self._on_context_matched: Optional[Callable] = None
        self._handlers = []
        self._active = False
        self._app = None

        if FUSION_AVAILABLE:
            try:
                self._app = adsk.core.Application.get()
            except:
                pass

    def start_watching(
        self,
        required: Dict[str, Any],
        on_matched: Callable[[Dict[str, Any]], None]
    ):
        """
        Start watching for context changes using Fusion events.

        Args:
            required: The required context dictionary.
            on_matched: Callback fired when context matches.
        """
        if not FUSION_AVAILABLE or not self._app:
            return

        self._required_context = required
        self._on_context_matched = on_matched
        self._active = True

        try:
            # Watch workspace changes
            ui = self._app.userInterface
            workspace_activated_handler = WorkspaceActivatedHandler(self)
            ui.workspaceActivated.add(workspace_activated_handler)
            self._handlers.append(workspace_activated_handler)

        except Exception as e:
            print(f"Error setting up event watching: {e}")

    def stop_watching(self):
        """Stop watching for context changes."""
        self._active = False
        self._handlers.clear()
        self._required_context = {}
        self._on_context_matched = None

    def on_workspace_changed(self):
        """Called when workspace changes."""
        if not self._active:
            return

        if self.context_detector.matches_requirements(self._required_context):
            context_dict = self.context_detector.get_current_context().to_dict()
            self._active = False

            if self._on_context_matched:
                self._on_context_matched(context_dict)


if FUSION_AVAILABLE:
    class WorkspaceActivatedHandler(adsk.core.WorkspaceEventHandler):
        """Handler for workspace activation events."""

        def __init__(self, polling_handler: 'FusionEventPollingHandler'):
            super().__init__()
            self.polling_handler = polling_handler

        def notify(self, args: adsk.core.WorkspaceEventArgs):
            self.polling_handler.on_workspace_changed()
