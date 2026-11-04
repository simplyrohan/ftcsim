"""Continuous-rotation servo using the shared PWM registers."""
from .base import number
from .servo import Servo


class CRServo(Servo):
    kind = 'cr_servo'
    display_name = 'CR servo'
    option_metadata = {
        **Servo.option_metadata,
        'max_rpm': {'label': 'Maximum RPM', 'min': 0.01},
        'direction': {'label': 'Physical direction', 'choices': [1, -1]},
    }

    def __init__(self, name, port, min_pulse_us=600, max_pulse_us=2400, max_rpm=60, direction=1):
        super().__init__(name, port, min_pulse_us, max_pulse_us)
        self.max_rpm = number(max_rpm, 'max_rpm', positive=True)
        if type(direction) is not int or direction not in (-1, 1):
            raise ValueError('Servo direction must be 1 or -1')
        self.direction = direction
        self.position = self.velocity = 0.0

    @property
    def power(self):
        return self.normalized_pulse * 2 - 1 if self.enabled else 0.0

    def step(self, dt, motion):
        self.velocity = self.power * self.max_rpm / 60 * self.direction
        self.position += self.velocity * dt

    def failsafe(self):
        super().failsafe()
        self.velocity = 0.0

    def state(self):
        return {**super().state(), 'power': self.power, 'velocity': self.velocity,
                'shaft_rpm': self.velocity * 60, 'max_rpm': self.max_rpm, 'direction': self.direction}
