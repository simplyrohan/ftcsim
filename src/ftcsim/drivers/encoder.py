"""Common encoder state, including signed 32-bit hardware counter wrapping."""

from .base import Driver


class Encoder(Driver):
    connection = "encoder"

    def __init__(self, name, port):
        super().__init__(name, port)
        self.position = 0.0
        self.velocity = 0.0

    @property
    def ticks(self):
        return (int(self.position) + 2**31) % 2**32 - 2**31

    def reset(self):
        self.position = 0.0

    def state(self):
        return {
            "position": self.position,
            "velocity": self.velocity,
            "ticks": self.ticks,
        }

    def failsafe(self):
        super().failsafe()
        self.velocity = 0.0
