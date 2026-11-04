"""Planar pose integration in millimeters and radians."""
from dataclasses import dataclass
import math


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
        return {'x_mm': self.x, 'y_mm': self.y, 'heading_rad': self.heading}

