import threading
import time
from pynput.keyboard import Controller, Key


class GameKeyOutput:
    """Send short taps / held keys to the currently focused game window."""

    def __init__(self):
        self.keyboard = Controller()
        self.enabled = False
        self._held = set()
        self._lock = threading.Lock()
        self.last_key = "-"
        self.last_action = "IDLE"

    def set_enabled(self, enabled: bool):
        with self._lock:
            self.enabled = bool(enabled)
            if not self.enabled:
                self.release_all()

    def tap(self, key: str, duration: float = 0.045, action: str = ""):
        if not self.enabled:
            return
        with self._lock:
            self.keyboard.press(key)
            time.sleep(max(0.02, min(duration, 0.12)))
            self.keyboard.release(key)
            self.last_key = key.upper()
            self.last_action = action or key.upper()

    def hold(self, key: str, active: bool, action: str = ""):
        with self._lock:
            if not self.enabled:
                if key in self._held:
                    try:
                        self.keyboard.release(key)
                    except Exception:
                        pass
                    self._held.discard(key)
                return

            if active and key not in self._held:
                self.keyboard.press(key)
                self._held.add(key)
                self.last_key = key.upper()
                self.last_action = action or key.upper()
            elif not active and key in self._held:
                self.keyboard.release(key)
                self._held.discard(key)

    def release_all(self):
        for key in list(self._held):
            try:
                self.keyboard.release(key)
            except Exception:
                pass
        self._held.clear()
