"""Ideal differential drive with one or two motors per side."""
from .drivetrain import Drivetrain, mounting_options
from ..drivers import BodyMotion, DCMotor


class TankDrivetrain(Drivetrain):
    kind = 'tank'
    display_name = 'Tank drivetrain'
    description = 'Left/right drive with optional rear motors and Pinpoint. Each side uses its average wheel speed; there is no lateral motion.'
    WHEELS = ('left', 'right', 'rear_left', 'rear_right')
    driver_slots = {
        **{wheel: {'label': f'{wheel.replace("_", " ").capitalize()} motor' + (' (optional)' if wheel.startswith('rear_') else ''),
                   'driver': DCMotor, 'required': wheel in ('left', 'right')} for wheel in WHEELS},
        **Drivetrain.driver_slots,
    }
    option_metadata = {**Drivetrain.option_metadata, **mounting_options(WHEELS)}

    def __init__(self, name, drivers, wheel_diameter_mm=96, gear_ratio=1,
                 wheelbase_mm=360, track_width_mm=360,
                 left_direction=1, right_direction=1, rear_left_direction=1, rear_right_direction=1):
        directions = {'left': left_direction, 'right': right_direction,
                      'rear_left': rear_left_direction, 'rear_right': rear_right_direction}
        super().__init__(name, drivers, wheel_diameter_mm, gear_ratio, wheelbase_mm, track_width_mm, directions)

    def wheel_motion(self, speeds):
        left = [speed for role, speed in speeds.items() if role in ('left', 'rear_left')]
        right = [speed for role, speed in speeds.items() if role in ('right', 'rear_right')]
        left, right = sum(left) / len(left), sum(right) / len(right)
        return BodyMotion((left + right) / 2, 0, (right - left) / self.track_width)
