"""Internal mechanism lifecycle. Mechanisms reference drivers; they do not own SDK devices."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
from ..drivers import BodyMotion


@dataclass
class Pose2D:
    x: float = 0
    y: float = 0
    heading: float = 0

    def advance(self, dt, motion):
        turn = motion.angular_velocity * dt
        sinc = math.sin(turn) / turn if abs(turn) > 1e-9 else 1
        cosc = (1 - math.cos(turn)) / turn if abs(turn) > 1e-9 else turn / 2
        forward = dt * (sinc * motion.vx - cosc * motion.vy)
        left = dt * (cosc * motion.vx + sinc * motion.vy)
        c, s = math.cos(self.heading), math.sin(self.heading)
        self.x += c * forward - s * left
        self.y += s * forward + c * left
        self.heading = (self.heading + turn + math.pi) % (2 * math.pi) - math.pi

    def snapshot(self):
        return dict(x_mm=self.x, y_mm=self.y, heading_rad=self.heading)


class Mechanism(ABC):
    kind = ''
    exclusive = True
    driver_slots = {}
    option_metadata = {}

    def __init__(self, name, drivers):
        self.name = name
        self.drivers = drivers
        self.motion = BodyMotion()

    @property
    def consumed_drivers(self):
        return tuple(self.drivers.values()) if self.exclusive else ()

    def sensor_inputs(self):
        """Root sensor → body motion. Robot advances each driver tree exactly once."""
        return {}

    @abstractmethod
    def advance(self, dt):
        """Read current actuator state and update the physical mechanism model."""

    def failsafe(self):
        self.motion = BodyMotion()

    @abstractmethod
    def state(self):
        pass

    def snapshot(self):
        return dict(name=self.name, type=self.kind,
                    drivers={role: driver.name for role, driver in self.drivers.items()},
                    state=self.state())
