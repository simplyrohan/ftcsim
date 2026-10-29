"""Ideal X-roller mecanum kinematics. Forward/left: mm/s; CCW yaw: radians/s."""
import math
from .base import Mechanism, Pose2D
from ..drivers import BodyMotion, DCMotor, GoBildaPinpoint, OdometryPod
from ..drivers.base import number


class MecanumDrivetrain(Mechanism):
    kind = 'mecanum'
    display_name = 'Mecanum drivetrain'
    description = ('Wheel speeds use each motor’s RPM, encoder resolution, and physical direction. '
                   'Mounting directions additionally reverse individual wheels. A selected Pinpoint uses its two '
                   'existing child pods and their physical mounting settings.')
    WHEELS = ('front_left', 'front_right', 'rear_left', 'rear_right')
    driver_slots = {
        'front_left': dict(label='Front left motor', driver=DCMotor, required=True),
        'front_right': dict(label='Front right motor', driver=DCMotor, required=True),
        'rear_left': dict(label='Rear left motor', driver=DCMotor, required=True),
        'rear_right': dict(label='Rear right motor', driver=DCMotor, required=True),
        'pinpoint': dict(label='Pinpoint with X/Y pods (optional)', driver=GoBildaPinpoint, required=False,
                         children={axis: dict(type='odometry', options=dict(axis=axis)) for axis in ('x', 'y')}),
    }
    option_metadata = {
        'wheel_diameter_mm': dict(label='Wheel diameter (mm)', min=0.01),
        'gear_ratio': dict(label='External gearing (motor output turns per wheel turn)', min=0.01),
        'wheelbase_mm': dict(label='Front-to-rear wheel spacing (mm)', min=0.01),
        'track_width_mm': dict(label='Left-to-right wheel spacing (mm)', min=0.01),
        'lateral_multiplier': dict(label='Lateral motion multiplier', min=0.01),
        **{f'{wheel}_direction': dict(label=f'{wheel.replace("_", " ").title()} mounting direction', choices=[dict(value=1, label='Forward'), dict(value=-1, label='Reversed')])
           for wheel in WHEELS},
    }

    def __init__(self, name, drivers, wheel_diameter_mm=96, gear_ratio=1,
                 wheelbase_mm=360, track_width_mm=360, lateral_multiplier=1,
                 front_left_direction=1, front_right_direction=1,
                 rear_left_direction=1, rear_right_direction=1):
        super().__init__(name, drivers)
        diameter = number(wheel_diameter_mm, 'wheel_diameter_mm', positive=True)
        self.wheel_circumference = math.pi * diameter
        self.gear_ratio = number(gear_ratio, 'gear_ratio', positive=True)
        self.turn_radius = (number(wheelbase_mm, 'wheelbase_mm', positive=True) +
                            number(track_width_mm, 'track_width_mm', positive=True)) / 2
        self.lateral_multiplier = number(lateral_multiplier, 'lateral_multiplier', positive=True)
        self.directions = dict(zip(self.WHEELS, (front_left_direction, front_right_direction,
                                               rear_left_direction, rear_right_direction)))
        if any(type(value) is not int or value not in (-1, 1) for value in self.directions.values()):
            raise ValueError('Motor mounting directions must be 1 or -1')
        self.pinpoint = drivers.get('pinpoint')
        if self.pinpoint:
            for axis in ('x', 'y'):
                pod = self.pinpoint.children.get(axis)
                if not isinstance(pod, OdometryPod) or pod.axis != axis:
                    raise ValueError(f'{self.pinpoint.name} needs an {axis.upper()} odometry pod on input {axis}')
        self.pose = Pose2D()
        self.wheel_speeds = dict.fromkeys(self.WHEELS, 0.0)

    @property
    def consumed_drivers(self):
        return (*super().consumed_drivers, *(self.pinpoint.children.values() if self.pinpoint else ()))

    def advance(self, dt):
        self.wheel_speeds = {wheel: self.drivers[wheel].shaft_revolutions_per_second * self.wheel_circumference / self.gear_ratio * self.directions[wheel]
                             for wheel in self.WHEELS}
        fl, fr, rl, rr = (self.wheel_speeds[wheel] for wheel in self.WHEELS)
        self.motion = BodyMotion((fl + fr + rl + rr) / 4,
                                 (-fl + fr + rl - rr) / 4 * self.lateral_multiplier,
                                 (-fl + fr - rl + rr) / (4 * self.turn_radius))
        self.pose.advance(dt, self.motion)

    def sensor_inputs(self):
        return {self.pinpoint: self.motion} if self.pinpoint else {}

    def failsafe(self):
        super().failsafe()
        self.wheel_speeds = dict.fromkeys(self.WHEELS, 0.0)

    def state(self):
        return dict(pose=self.pose.snapshot(),
                    velocity=dict(vx_mm_s=self.motion.vx, vy_mm_s=self.motion.vy,
                                  yaw_rate_rad_s=self.motion.angular_velocity),
                    wheel_speeds_mm_s=self.wheel_speeds,
                    pinpoint=self.pinpoint.name if self.pinpoint else None,
                    encoders=[pod.name for pod in self.pinpoint.children.values()] if self.pinpoint else [],
                    # Read the same pod instances exposed under the Pinpoint in
                    # the hardware map, after the sensor phase has advanced them.
                    encoder_states=[dict(name=self.pinpoint.children[axis].name, port=axis,
                                         **self.pinpoint.children[axis].state())
                                    for axis in ('x', 'y')] if self.pinpoint else [])
