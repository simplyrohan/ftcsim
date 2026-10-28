"""Passive tracking wheel. Physical mounting is independent of Pinpoint settings."""
from .base import number
from .encoder import Encoder


class OdometryPod(Encoder):
    display_name = 'Odometry pod'
    option_metadata = {'axis': {'label': 'Tracking axis', 'choices': ['x', 'y']}, 'offset_mm': {'label': 'Physical mounting offset (mm)'}, 'ticks_per_mm': {'label': 'Encoder resolution (ticks/mm)', 'min': 0.01}, 'direction': {'label': 'Encoder wiring direction', 'choices': [1, -1]}}
    kind = 'odometry'

    def __init__(self, name, port, axis='x', offset_mm=0, ticks_per_mm=13.26291192, direction=1):
        super().__init__(name, port)
        if axis not in ('x', 'y') or direction not in (-1, 1) or isinstance(direction, bool):
            raise ValueError('Pod axis must be x/y and direction must be 1/-1')
        self.axis = axis
        self.offset = number(offset_mm, 'offset_mm')
        self.ticks_per_mm = number(ticks_per_mm, 'ticks_per_mm', positive=True)
        self.direction = direction

    def step(self, dt, motion):
        # x wheel is displaced left of center; y wheel is displaced forward.
        speed = motion.vx - motion.angular_velocity * self.offset if self.axis == 'x' else motion.vy + motion.angular_velocity * self.offset
        self.velocity = speed * self.ticks_per_mm * self.direction
        self.position += self.velocity * dt

    def state(self):
        return dict(super().state(), axis=self.axis, offset_mm=self.offset,
                    ticks_per_mm=self.ticks_per_mm, distance_mm=self.position / self.ticks_per_mm)
