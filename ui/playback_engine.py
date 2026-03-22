import time
from PySide6.QtCore import QObject, Signal, QTimer

class PlaybackEngine(QObject):
    """
    Manages animation state, frame interpolation, and timing for real-time playback.
    """
    frame_changed = Signal(int)
    time_changed = Signal(float)

    def __init__(self, fps: int = 30):
        """
        Initializes the PlaybackEngine.

        Args:
            fps: The target frames per second for playback.
        """
        super().__init__()
        self.fps = fps
        self.duration = 0.0
        self.current_time = 0.0
        self.is_playing = False
        self._last_tick = 0.0
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timeout)
        self.timer.setInterval(16)  # ~60 FPS update rate for smooth playback

    def set_duration(self, duration: float):
        """
        Sets the total duration of the animation in seconds.

        Args:
            duration: The duration in seconds.
        """
        self.duration = duration
        self.current_time = 0.0
        self.time_changed.emit(self.current_time)
        self.frame_changed.emit(0)

    def set_fps(self, fps: int):
        """
        Sets the target frames per second.

        Args:
            fps: The frames per second.
        """
        self.fps = fps

    def play(self):
        """Starts animation playback."""
        if self.duration > 0:
            self.is_playing = True
            self._last_tick = time.time()
            self.timer.start()

    def pause(self):
        """Pauses animation playback."""
        self.is_playing = False
        self.timer.stop()

    def reset(self):
        """Resets animation to the beginning."""
        self.pause()
        self.current_time = 0.0
        self.time_changed.emit(self.current_time)
        self.frame_changed.emit(0)

    def set_time(self, timestamp: float):
        """
        Sets the current playback time.

        Args:
            timestamp: The playback time in seconds.
        """
        if 0 <= timestamp <= self.duration:
            self.current_time = timestamp
            self.time_changed.emit(self.current_time)
            self.frame_changed.emit(int(self.current_time * self.fps))

    def _on_timeout(self):
        """Internal timer callback for updating playback time."""
        if not self.is_playing:
            return

        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        if self.duration > 0:
            self.current_time += dt
            if self.current_time >= self.duration:
                self.current_time = self.current_time % self.duration
        else:
            self.current_time = 0.0

        self.time_changed.emit(self.current_time)
        self.frame_changed.emit(int(self.current_time * self.fps))
