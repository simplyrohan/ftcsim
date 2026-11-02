"""DC motor dynamics and Lynx motor register protocol."""
import math
import struct
from .base import number
from .encoder import Encoder
from .motor_presets import GOBILDA_PRESETS


class DCMotor(Encoder):
    display_name = 'DC motor'
    option_metadata = {
        'max_rpm': {'label': 'Maximum RPM', 'min': 0.01},
        'ticks_per_revolution': {'label': 'Encoder ticks per output-shaft revolution', 'min': 0.01},
        'direction': {'label': 'Physical direction', 'choices': [{'value': 1, 'label': 'Forward'}, {'value': -1, 'label': 'Reversed'}]},
    }
    presets = GOBILDA_PRESETS
    kind = 'motor'
    phase = 'actuator'
    connection = 'motor'
    REGISTERS = {
        'MotorConstantPower': (2, bytes(2)),
        'MotorChannelMode': (2, b'\x00\x01'),
        'MotorChannelEnable': (1, b'\x00'),
        'MotorChannelCurrentAlertLevel': (2, b'\xff\x7f'),
        'MotorTargetVelocity': (2, bytes(2)),
        'MotorTargetPosition': (6, bytes(6)),
    }

    def __init__(self, name, port, max_rpm=312, ticks_per_revolution=537.7, direction=1):
        super().__init__(name, port)
        self.max_rpm = number(max_rpm, 'max_rpm', positive=True)
        self.ticks_per_revolution = number(ticks_per_revolution, 'ticks_per_revolution', positive=True)
        self.max_speed = number(self.max_rpm / 60 * self.ticks_per_revolution, 'maximum tick velocity', positive=True)
        if type(direction) is not int or direction not in (-1, 1):
            raise ValueError('Motor direction must be 1 (forward) or -1 (reversed)')
        self.direction = direction
        self.registers = {}

    @staticmethod
    def normalize_options(options):
        """Convert legacy tick-rate limits to RPM."""
        options = {**options}
        if 'max_ticks_per_second' in options:
            speed = number(options.pop('max_ticks_per_second'), 'max_ticks_per_second', positive=True)
            ticks = number(options.get('ticks_per_revolution', 537.7), 'ticks_per_revolution', positive=True)
            if 'max_rpm' in options:
                raise ValueError('Use max_rpm instead of max_ticks_per_second')
            options['max_rpm'] = speed / ticks * 60
        return options

    @property
    def shaft_revolutions_per_second(self):
        # Physical reversal does not change native encoder coordinates.
        return self.velocity / self.ticks_per_revolution * self.direction

    def register(self, name):
        return self.registers.get(name, self.REGISTERS[name][1])

    @property
    def enabled(self):
        return bool(self.register('MotorChannelEnable')[0])

    @property
    def mode(self):
        return self.register('MotorChannelMode')[0]

    @property
    def power(self):
        if not self.enabled:
            return 0.0
        suffix, scale = ('MotorTargetVelocity', self.max_speed) if self.mode in (1, 2) else ('MotorConstantPower', 32767)
        value, = struct.unpack('<h', self.register(suffix))
        return max(-1, min(1, value / scale))

    @property
    def at_target(self):
        target, tolerance = struct.unpack('<iH', self.register('MotorTargetPosition'))
        return abs(target - self.position) <= tolerance

    def step(self, dt, motion):
        velocity = self.power * self.max_speed
        if self.mode == 2:
            target, tolerance = struct.unpack('<iH', self.register('MotorTargetPosition'))
            delta = target - self.position
            velocity = math.copysign(min(abs(velocity), abs(delta) / dt), delta) if dt and abs(delta) > tolerance else 0
        self.velocity = velocity
        self.position += velocity * dt

    def handle_lynx(self, name, data):
        for suffix, (width, _) in self.REGISTERS.items():
            if name == f'LynxSet{suffix}Command':
                if len(data) != width:
                    raise ValueError('Invalid motor register width')
                self.registers[suffix] = data
                return b''
            if name == f'LynxGet{suffix}Command':
                if data:
                    raise ValueError('Unexpected motor read payload')
                return self.register(suffix)
        if 'PID' in name:
            width = 17 if 'PIDF' in name else 12
            key = name.replace('Set', 'Get'), data[:1]
            if 'Set' in name and len(data) == width + 1:
                self.registers[key] = data[1:]
                return b''
            if 'Get' in name and len(data) == 1:
                return self.registers.get(key, bytes(width))
            raise ValueError('Invalid PID payload')
        raise NotImplementedError(name)

    def failsafe(self):
        super().failsafe()
        self.registers['MotorChannelEnable'] = b'\x00'
        self.registers['MotorConstantPower'] = bytes(2)

    def state(self):
        return {**super().state(), 'enabled': self.enabled, 'mode': self.mode, 'power': self.power,
                'max_ticks_per_second': self.max_speed, 'max_rpm': self.max_rpm,
                'ticks_per_revolution': self.ticks_per_revolution, 'direction': self.direction,
                'shaft_rpm': self.shaft_revolutions_per_second * 60}
