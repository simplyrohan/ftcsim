"""Device lifecycle and shared physical inputs. Distances: mm; angles: radians."""
from dataclasses import dataclass
import math


def number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if positive and value <= 0:
        raise ValueError(f'{name} must be positive')
    return float(value)


@dataclass(frozen=True)
class BodyMotion:
    """Robot-relative forward/left velocity and counterclockwise yaw rate."""
    vx: float = 0
    vy: float = 0
    angular_velocity: float = 0


class Driver:
    kind = 'device'
    connection = ''
    child_ports = ()
    child_connections = {}
    child_defaults = {}

    def __init__(self, name, port):
        self.name = name
        self.port = port
        self.children = {}

    def attach(self, port, child):
        if port not in self.child_ports or port in self.children:
            raise ValueError(f'{self.name}: invalid or occupied child port {port}')
        if child.connection != self.child_connections.get(port):
            raise ValueError(f'{self.name}: incompatible child on {port}')
        self.children[port] = child

    def advance(self, dt, motion):
        for child in self.children.values():
            child.advance(dt, motion)
        self.step(dt, motion)

    def step(self, dt, motion):
        pass

    def failsafe(self):
        for child in self.children.values():
            child.failsafe()

    def state(self):
        return {}

    def snapshot(self):
        return dict(name=self.name, type=self.kind, port=self.port, connection=self.connection,
                    state=self.state(), children=[child.snapshot() for child in self.children.values()])
