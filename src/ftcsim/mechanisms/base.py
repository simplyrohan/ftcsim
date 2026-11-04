"""Internal mechanism lifecycle. Mechanisms reference drivers; they do not own SDK devices."""
from abc import ABC, abstractmethod
from ..drivers import BodyMotion
from ..geometry import Pose2D


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
        return {'name': self.name, 'type': self.kind,
                'drivers': {role: driver.name for role, driver in self.drivers.items()},
                'state': self.state()}
