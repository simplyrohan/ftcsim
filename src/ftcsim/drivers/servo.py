"""PWM servo command model. No load/torque or travel-time simulation."""
import struct
from .base import Driver, number


class Servo(Driver):
    display_name = 'Servo'
    option_metadata = {'min_pulse_us': {'label': 'Minimum pulse (µs)', 'min': 0.01}, 'max_pulse_us': {'label': 'Maximum pulse (µs)', 'min': 0.01}}
    kind = 'servo'
    connection = 'servo'
    REGISTERS = {'ServoConfiguration': (2, struct.pack('<H', 20000)),
                 'ServoPulseWidth': (2, struct.pack('<H', 1500)), 'ServoEnable': (1, b'\x00')}

    def __init__(self, name, port, min_pulse_us=500, max_pulse_us=2500):
        super().__init__(name, port)
        self.minimum = number(min_pulse_us, 'min_pulse_us', positive=True)
        self.maximum = number(max_pulse_us, 'max_pulse_us', positive=True)
        if self.maximum <= self.minimum:
            raise ValueError('max_pulse_us must exceed min_pulse_us')
        self.registers = {}
        self.position = 0.5

    def register(self, suffix):
        return self.registers.get(suffix, self.REGISTERS[suffix][1])

    @property
    def enabled(self):
        return bool(self.register('ServoEnable')[0])

    def step(self, dt, motion):
        if self.enabled:
            pulse, = struct.unpack('<H', self.register('ServoPulseWidth'))
            self.position = max(0, min(1, (pulse - self.minimum) / (self.maximum - self.minimum)))

    def handle_lynx(self, name, data):
        for suffix, (width, _) in self.REGISTERS.items():
            if name == f'LynxSet{suffix}Command':
                if len(data) != width:
                    raise ValueError('Invalid servo register width')
                self.registers[suffix] = data
                return b''
            if name == f'LynxGet{suffix}Command':
                if data:
                    raise ValueError('Unexpected servo read payload')
                return self.register(suffix)
        raise NotImplementedError(name)

    def failsafe(self):
        super().failsafe()
        self.registers['ServoEnable'] = b'\x00'

    def state(self):
        return dict(enabled=self.enabled, position=self.position,
                    pulse_us=struct.unpack('<H', self.register('ServoPulseWidth'))[0],
                    period_us=struct.unpack('<H', self.register('ServoConfiguration'))[0])
