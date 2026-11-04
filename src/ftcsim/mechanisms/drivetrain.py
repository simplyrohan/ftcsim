"""Shared wheel geometry, chassis pose, placement, and odometry binding."""
import math
from abc import abstractmethod
from .base import Mechanism, Pose2D
from ..drivers import DCMotor, GoBildaPinpoint, OdometryPod
from ..drivers.base import number


def mounting_options(wheels):
    return {f'{wheel}_direction': {
        'label': f'{wheel.replace("_", " ").title()} mounting direction',
        'choices': [{'value': 1, 'label': 'Forward'}, {'value': -1, 'label': 'Reversed'}],
    } for wheel in wheels}


class Drivetrain(Mechanism):
    driver_slots = {
        'pinpoint': {'label': 'Pinpoint with X/Y pods (optional)', 'driver': GoBildaPinpoint, 'required': False,
                     'children': {axis: {'type': 'odometry', 'options': {'axis': axis}} for axis in ('x', 'y')}},
    }
    option_metadata = {
        'wheel_diameter_mm': {'label': 'Wheel diameter (mm)', 'min': 0.01},
        'gear_ratio': {'label': 'External gearing (motor output turns per wheel turn)', 'min': 0.01},
        'wheelbase_mm': {'label': 'Front-to-rear wheel spacing (mm)', 'min': 0.01},
        'track_width_mm': {'label': 'Left-to-right wheel spacing (mm)', 'min': 0.01},
    }

    def __init__(self, name, drivers, wheel_diameter_mm, gear_ratio, wheelbase_mm, track_width_mm, directions):
        super().__init__(name, drivers)
        self.wheel_circumference = math.pi * number(wheel_diameter_mm, 'wheel_diameter_mm', positive=True)
        self.gear_ratio = number(gear_ratio, 'gear_ratio', positive=True)
        self.wheelbase = number(wheelbase_mm, 'wheelbase_mm', positive=True)
        self.track_width = number(track_width_mm, 'track_width_mm', positive=True)
        self.directions = directions
        if any(type(value) is not int or value not in (-1, 1) for value in directions.values()):
            raise ValueError('Motor mounting directions must be 1 or -1')
        self.motors = {role: driver for role, driver in drivers.items() if isinstance(driver, DCMotor)}
        self.pinpoint = drivers.get('pinpoint')
        if self.pinpoint:
            for axis in ('x', 'y'):
                pod = self.pinpoint.children.get(axis)
                if not isinstance(pod, OdometryPod) or pod.axis != axis:
                    raise ValueError(f'{self.pinpoint.name} needs an {axis.upper()} odometry pod on input {axis}')
        self.pose = Pose2D()
        self.wheel_speeds = dict.fromkeys(self.motors, 0.0)

    @property
    def consumed_drivers(self):
        return (*super().consumed_drivers, *(self.pinpoint.children.values() if self.pinpoint else ()))

    def advance(self, dt):
        self.wheel_speeds = {role: motor.shaft_revolutions_per_second * self.wheel_circumference /
                             self.gear_ratio * self.directions[role] for role, motor in self.motors.items()}
        self.motion = self.wheel_motion(self.wheel_speeds)
        self.pose.advance(dt, self.motion)

    @abstractmethod
    def wheel_motion(self, speeds):
        raise NotImplementedError

    def sensor_inputs(self):
        return {self.pinpoint: self.motion} if self.pinpoint else {}

    def place(self, x_mm, y_mm, heading_deg):
        """Place the chassis without changing encoder or IMU coordinates."""
        x, y = number(x_mm, 'x_mm'), number(y_mm, 'y_mm')
        heading = math.radians(number(heading_deg, 'heading_deg'))
        if any(abs(motor.shaft_revolutions_per_second) > 1e-6 for motor in self.motors.values()):
            raise ValueError('Stop the drivetrain before changing its start position')
        self.pose = Pose2D(x, y, (heading + math.pi) % (2 * math.pi) - math.pi)
        self.failsafe()

    def failsafe(self):
        super().failsafe()
        self.wheel_speeds = dict.fromkeys(self.motors, 0.0)

    def state(self):
        return {'pose': self.pose.snapshot(),
                'velocity': {'vx_mm_s': self.motion.vx, 'vy_mm_s': self.motion.vy,
                             'yaw_rate_rad_s': self.motion.angular_velocity},
                'wheel_speeds_mm_s': self.wheel_speeds,
                'pinpoint': self.pinpoint.name if self.pinpoint else None,
                'encoders': [pod.name for pod in self.pinpoint.children.values()] if self.pinpoint else [],
                'encoder_states': [{'name': self.pinpoint.children[axis].name, 'port': axis,
                                    **self.pinpoint.children[axis].state()}
                                   for axis in ('x', 'y')] if self.pinpoint else []}
