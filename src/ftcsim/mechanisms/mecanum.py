"""Ideal X-roller mecanum kinematics. Forward/left: mm/s; CCW yaw: radians/s."""
from .drivetrain import Drivetrain, mounting_options
from ..drivers import BodyMotion, DCMotor
from ..drivers.base import number


class MecanumDrivetrain(Drivetrain):
    kind = 'mecanum'
    display_name = 'Mecanum drivetrain'
    description = 'Four X-roller wheels with optional Pinpoint and two odometry pods. Motor speed and physical direction come from the hardware map.'
    WHEELS = ('front_left', 'front_right', 'rear_left', 'rear_right')
    driver_slots = {
        **{wheel: {'label': f'{wheel.replace("_", " ").capitalize()} motor', 'driver': DCMotor, 'required': True}
           for wheel in WHEELS},
        **Drivetrain.driver_slots,
    }
    option_metadata = {
        **Drivetrain.option_metadata,
        'lateral_multiplier': {'label': 'Lateral motion multiplier', 'min': 0.01},
        **mounting_options(WHEELS),
    }

    def __init__(self, name, drivers, wheel_diameter_mm=96, gear_ratio=1,
                 wheelbase_mm=360, track_width_mm=360, lateral_multiplier=1,
                 front_left_direction=1, front_right_direction=1,
                 rear_left_direction=1, rear_right_direction=1):
        directions = {'front_left': front_left_direction, 'front_right': front_right_direction,
                      'rear_left': rear_left_direction, 'rear_right': rear_right_direction}
        super().__init__(name, drivers, wheel_diameter_mm, gear_ratio, wheelbase_mm, track_width_mm, directions)
        self.turn_radius = (self.wheelbase + self.track_width) / 2
        self.lateral_multiplier = number(lateral_multiplier, 'lateral_multiplier', positive=True)

    def wheel_motion(self, speeds):
        fl, fr, rl, rr = (speeds[wheel] for wheel in self.WHEELS)
        return BodyMotion((fl + fr + rl + rr) / 4,
                          (-fl + fr + rl - rr) / 4 * self.lateral_multiplier,
                          (-fl + fr - rl + rr) / (4 * self.turn_radius))
