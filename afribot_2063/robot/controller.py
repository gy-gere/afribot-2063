"""
robot/controller.py — AfriBot physical robot interface (future deployment).

This module provides a clean abstraction so main.py works identically
whether running on a desktop or on the physical AfriBot hardware.

GPIO, servos, LEDs, and other hardware are activated only when
ROBOT_MODE = True in config (or when the hardware is detected).
"""

import time
from utils.logger import get_logger

log = get_logger("robot")


class RobotController:
    """
    Abstracts all physical robot I/O.
    On desktop: all methods are no-ops (safe to call).
    On AfriBot hardware: controls GPIO, display, LEDs, etc.
    """

    def __init__(self):
        self.hardware_available = self._detect_hardware()
        if self.hardware_available:
            self._init_hardware()
        else:
            log.info("Running in desktop/simulation mode (no hardware detected)")

    # ── Hardware detection ────────────────────────────────────────────────

    def _detect_hardware(self) -> bool:
        """Returns True if running on Raspberry Pi / AfriBot hardware."""
        try:
            with open("/proc/device-tree/model", "r") as f:
                model = f.read()
            if "Raspberry Pi" in model or "AfriBot" in model:
                log.info(f"Hardware detected: {model.strip()}")
                return True
        except Exception:
            pass
        return False

    def _init_hardware(self):
        """Initialise GPIO pins, display, LEDs."""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            # LED pins (customise for your AfriBot wiring)
            self.LED_THINKING = 17
            self.LED_SPEAKING  = 27
            GPIO.setup(self.LED_THINKING, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self.LED_SPEAKING,  GPIO.OUT, initial=GPIO.LOW)
            self._gpio = GPIO
            log.info("GPIO initialised")
        except ImportError:
            log.warning("RPi.GPIO not available — hardware mode disabled")
            self.hardware_available = False

    # ── Status indicators ─────────────────────────────────────────────────

    def set_thinking(self, active: bool = True):
        """Flash LED / display when AfriBot is processing."""
        log.debug(f"[Robot] thinking={'on' if active else 'off'}")
        if self.hardware_available:
            self._gpio.output(self.LED_THINKING, active)

    def set_speaking(self, active: bool = True):
        """Flash LED / display when AfriBot is speaking."""
        log.debug(f"[Robot] speaking={'on' if active else 'off'}")
        if self.hardware_available:
            self._gpio.output(self.LED_SPEAKING, active)

    def display_text(self, text: str, line: int = 1):
        """Show text on LCD or OLED display if available."""
        log.debug(f"[Robot] display L{line}: {text[:20]}")
        # TODO: integrate with Adafruit CircuitPython LCD library
        # Example:  lcd.message = text[:16]

    def greet(self):
        """Startup greeting sequence."""
        self.set_thinking(False)
        self.set_speaking(True)
        time.sleep(0.5)
        self.set_speaking(False)
        log.info("[Robot] Greeting sequence complete")

    def cleanup(self):
        """Clean up GPIO on shutdown."""
        if self.hardware_available:
            try:
                self._gpio.cleanup()
                log.info("GPIO cleaned up")
            except Exception as e:
                log.warning(f"GPIO cleanup error: {e}")


# Singleton instance — import and use anywhere
robot = RobotController()
