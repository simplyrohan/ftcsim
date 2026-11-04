"""OctoQuad firmware 3.1 encoder banks and MK2 planar localizer."""
from copy import deepcopy
import math
import struct
from .base import BodyMotion, number
from .encoder import Encoder
from .odometry import OdometryPod
from .i2c import I2CDriver
from ..geometry import Pose2D


def signed(value, bits):
    return (int(value) + 2**(bits - 1)) % 2**bits - 2**(bits - 1)


class OctoQuadEncoder(OdometryPod):
    kind = 'octoquad_encoder'
    display_name = 'OctoQuad encoder / tracking wheel'
    option_metadata = {
        **OdometryPod.option_metadata,
        'ticks_per_revolution': {'label': 'Physical encoder ticks / revolution', 'min': .01},
        'min_pulse_us': {'label': 'Physical PWM minimum (µs)', 'min': 0, 'max': 65535},
        'max_pulse_us': {'label': 'Physical PWM maximum (µs)', 'min': 0, 'max': 65535},
    }

    def __init__(self, name, port, axis='x', offset_mm=0, ticks_per_mm=13.26291192,
                 direction=1, ticks_per_revolution=2000, min_pulse_us=1, max_pulse_us=1024):
        super().__init__(name, port, axis, offset_mm, ticks_per_mm, direction)
        self.ticks_per_revolution = number(ticks_per_revolution, 'ticks_per_revolution', positive=True)
        self.min_pulse = number(min_pulse_us, 'min_pulse_us')
        self.max_pulse = number(max_pulse_us, 'max_pulse_us')
        if not 0 <= self.min_pulse < self.max_pulse <= 65535:
            raise ValueError('PWM pulse limits must satisfy 0 ≤ minimum < maximum ≤ 65535 µs')

    @property
    def pulse_width(self):
        return self.min_pulse + (self.position / self.ticks_per_revolution % 1) * (self.max_pulse - self.min_pulse)

    def state(self):
        return {**super().state(), 'pulse_width_us': self.pulse_width,
                'ticks_per_revolution': self.ticks_per_revolution}


class OctoQuad(I2CDriver):
    address = 0x30
    has_imu = False
    child_ports = tuple(str(i) for i in range(8))
    child_connections = {str(i): 'encoder' for i in range(8)}
    child_defaults = {str(i): {'axis': 'x' if i % 2 == 0 else 'y'} for i in range(8)}
    default_child_ports = ('0', '1')
    default_child_type = 'octoquad_encoder'

    @staticmethod
    def default_parameters():
        return {0: 0, 1: 0, 2: 0, 3: [50] * 8, 4: [(1, 1024)] * 8, 5: 0,
                       50: 1., 51: 1., 52: 0., 53: 0., 54: 1., 55: 0, 56: 1, 57: 25}

    def __init__(self, name, port):
        super().__init__(name, port)
        self.params = self.default_parameters()
        self.saved_params = deepcopy(self.params)
        self.operands = bytes(7)
        self.uptime = 0.
        self.zeros = [0.] * 8
        self.wrap_zeros = [0] * 8
        self.velocities = [0] * 8
        self.sample_previous = [0.] * 8
        self.sample_elapsed = [0.] * 8
        self.pose = Pose2D()
        self.vx = self.vy = self.yaw_rate = 0.
        self.localizer_started = False
        self.calibration = 0.
        self.localizer_params = deepcopy(self.params)
        self.localizer_previous = [0, 0]
        self.localizer_velocity_elapsed = 0.
        self.localizer_yaw_delta = 0.
        self.localizer_velocity_previous = (0., 0., 0.)

    def attach(self, port, child):
        if not isinstance(child, Encoder):
            raise ValueError('OctoQuad inputs require Encoder drivers')
        super().attach(port, child)
        self.sample_previous[int(port)] = self.channel_value(int(port), continuous=True)
        self.align_localizer()

    def pwm(self, channel):
        return self.params[2] == 1 or self.params[2] == 2 and channel >= 4

    def channel_value(self, channel, *, continuous=False):
        child = self.children.get(str(channel))
        if child is None:
            return 0.
        direction = -1 if self.params[0] & (1 << channel) else 1
        if not self.pwm(channel):
            return (child.position - (0 if continuous else self.zeros[channel])) * direction
        if not isinstance(child, OctoQuadEncoder):
            return 0.  # This input has no physical PWM signal.
        minimum, maximum = self.params[4][channel]
        pulse = child.pulse_width if direction == 1 else minimum + maximum - child.pulse_width
        wraps = math.floor(child.position / child.ticks_per_revolution) * direction
        if continuous or self.params[5] & (1 << channel):
            pulse += (wraps - (0 if continuous else self.wrap_zeros[channel])) * (maximum - minimum)
        return pulse

    def positions(self):
        return [signed(self.channel_value(i), 32) for i in range(8)]

    @property
    def status(self):
        if not self.has_imu:
            return 5
        if not self.localizer_started:
            return 1
        return (2 if self.calibration > .2 else 3) if self.calibration > 0 else 4

    def align_localizer(self):
        positions = self.positions()
        self.localizer_previous = [positions[self.localizer_params[key]] for key in (55, 56)]

    def reset_localizer(self):
        self.localizer_params = deepcopy(self.params)
        self.pose = Pose2D()
        self.vx = self.vy = self.yaw_rate = 0.
        self.localizer_started = self.has_imu
        self.calibration = .3 if self.has_imu else 0.
        self.localizer_velocity_elapsed = 0.
        self.localizer_yaw_delta = 0.
        self.localizer_velocity_previous = (0., 0., 0.)
        self.align_localizer()

    def step(self, dt, motion):
        self.uptime += dt
        for channel in range(8):
            self.sample_elapsed[channel] += dt
            interval = self.params[3][channel] / 1000
            if self.sample_elapsed[channel] + 1e-9 >= interval:
                value = self.channel_value(channel, continuous=True)
                delta = value - self.sample_previous[channel]
                self.velocities[channel] = signed(round(delta * interval / self.sample_elapsed[channel]), 16)
                self.sample_previous[channel] = value
                self.sample_elapsed[channel] = 0.
        positions = self.positions()
        current = [positions[self.localizer_params[key]] for key in (55, 56)]
        delta = [signed(value - previous, 32) for value, previous in zip(current, self.localizer_previous)]
        self.localizer_previous = current
        if self.status != 4:
            self.calibration = max(0., self.calibration - dt)
            return
        params = self.localizer_params
        yaw = motion.angular_velocity * params[54]
        dx = delta[0] / params[50] - params[53] * yaw * dt
        dy = delta[1] / params[51] + params[52] * yaw * dt
        if dt:
            self.pose.advance(dt, BodyMotion(dx / dt, dy / dt, yaw))
        self.localizer_velocity_elapsed += dt
        self.localizer_yaw_delta += yaw * dt
        if self.localizer_velocity_elapsed + 1e-9 >= params[57] / 1000:
            px, py, _ = self.localizer_velocity_previous
            elapsed = self.localizer_velocity_elapsed
            self.vx, self.vy = (self.pose.x - px) / elapsed, (self.pose.y - py) / elapsed
            self.yaw_rate = self.localizer_yaw_delta / elapsed
            self.localizer_velocity_previous = (self.pose.x, self.pose.y, self.pose.heading)
            self.localizer_velocity_elapsed = 0.
            self.localizer_yaw_delta = 0.

    @staticmethod
    def crc(data):
        value = 0xffff
        for byte in data:
            value ^= byte << 8
            for _ in range(8):
                value = ((value << 1) ^ (0x1dcf if value & 0x8000 else 0)) & 0xffff
        return value ^ 0xffff

    def read(self, register, count):
        if register < 0 or count < 0 or register + count > 0x4e:
            raise ValueError('Invalid OctoQuad register read')
        data = bytearray(0x4e)
        data[:4] = bytes([0x51, 3, 1, 0])
        data[5:12] = self.operands
        data[12] = 5 if self.status == 4 else 0
        localizer = struct.pack('<B6h', self.status, *[signed(value, 16) for value in
                                (self.vx, self.vy, self.yaw_rate * 600, self.pose.x, self.pose.y, self.pose.heading * 5000)])
        data[13:28] = localizer + struct.pack('<H', self.crc(localizer))
        encoders = struct.pack('<8i8h', *self.positions(), *self.velocities)
        data[28:78] = encoders + struct.pack('<H', self.crc(encoders))
        return bytes(data[register:register + count])

    def parameter(self, key, arguments, *, write=False):
        if key in (200, 201) and not write:
            return struct.pack('<I', int(self.uptime * 1000) % 2**32 if key == 200 else 0)
        if key not in self.params:
            raise ValueError(f'Unknown OctoQuad parameter {key}')
        channel = None
        if key in (3, 4):
            if not arguments or arguments[0] > 7:
                raise ValueError('OctoQuad channel must be 0–7')
            channel, arguments = arguments[0], arguments[1:]
        fmt = '<f' if 50 <= key <= 54 else '<2H' if key == 4 else '<B'
        if write:
            if len(arguments) != struct.calcsize(fmt):
                raise ValueError('Invalid OctoQuad parameter length')
            values = struct.unpack(fmt, arguments)
            value = values if key == 4 else values[0]
            if key in (1, 2) and value not in (0, 1, 2) or key in (55, 56) and value > 7:
                raise ValueError('Invalid OctoQuad parameter value')
            if 50 <= key <= 54:
                number(value, 'OctoQuad parameter', positive=key in (50, 51, 54))
            if key == 4 and value[0] >= value[1]:
                raise ValueError('PWM maximum must exceed minimum')
            if key in (3, 57) and value == 0:
                return b''
            if key == 0:
                for index in range(8):
                    if (self.params[0] ^ value) & (1 << index):
                        self.wrap_zeros[index] *= -1
            if channel is None:
                self.params[key] = value
            else:
                self.params[key][channel] = value
            if key in (0, 2, 4):
                self.sample_previous = [self.channel_value(i, continuous=True) for i in range(8)]
                self.sample_elapsed = [0.] * 8
                self.align_localizer()
            return b''
        value = self.params[key] if channel is None else self.params[key][channel]
        return struct.pack(fmt, *(value if key == 4 else (value,)))

    def write(self, register, data):
        if register == 4:
            if not data:
                raise ValueError('Missing OctoQuad command')
            command, arguments = data[0], data[1:]
            if command == 0:
                return
            if command in (1, 2):
                if not arguments:
                    raise ValueError('Missing OctoQuad parameter ID')
                result = self.parameter(arguments[0], arguments[1:], write=command == 1)
                if command == 2:
                    self.operands = result.ljust(7, b'\0')
            elif command == 3:
                self.saved_params = deepcopy(self.params)
            elif command in (20, 21):
                if command == 20:
                    self.params = self.default_parameters()
                    mask = 255
                    self.reset_localizer()
                    self.localizer_started = False
                else:
                    if len(arguments) != 1:
                        raise ValueError('Encoder reset requires a channel bitfield')
                    mask = arguments[0]
                for channel in range(8):
                    child = self.children.get(str(channel))
                    if child is not None and mask & (1 << channel):
                        self.zeros[channel] = child.position
                        direction = -1 if self.params[0] & (1 << channel) else 1
                        self.wrap_zeros[channel] = math.floor(child.position / child.ticks_per_revolution) * direction if isinstance(child, OctoQuadEncoder) else 0
                        self.velocities[channel] = 0
                        self.sample_previous[channel] = self.channel_value(channel, continuous=True)
                        self.sample_elapsed[channel] = 0.
                self.align_localizer()
            elif command == 40:
                self.reset_localizer()
            else:
                raise ValueError(f'Unknown OctoQuad command {command}')
            return
        if 0x14 <= register and register + len(data) <= 0x1a and register % 2 == 0 and len(data) % 2 == 0:
            values = struct.unpack('<' + 'h' * (len(data) // 2), data)
            for offset, value in enumerate(values):
                setattr(self.pose, ('x', 'y', 'heading')[(register - 0x14) // 2 + offset], value / 5000 if register + offset * 2 == 0x18 else value)
            self.localizer_velocity_previous = (self.pose.x, self.pose.y, self.pose.heading)
            self.localizer_velocity_elapsed = 0.
            self.localizer_yaw_delta = 0.
            self.vx = self.vy = self.yaw_rate = 0.
            return
        raise ValueError(f'Read-only/unsupported OctoQuad register {register}')

    def power_cycle(self):
        children, saved = self.children, deepcopy(self.saved_params)
        OctoQuad.__init__(self, self.name, self.port)
        self.params, self.saved_params = saved, deepcopy(saved)
        self.localizer_params = deepcopy(saved)
        for port, child in children.items():
            self.attach(port, child)
        self.write(4, bytes([21, 255]))

    def failsafe(self):
        super().failsafe()
        self.velocities = [0] * 8
        self.sample_previous = [self.channel_value(i, continuous=True) for i in range(8)]
        self.sample_elapsed = [0.] * 8
        self.vx = self.vy = self.yaw_rate = 0.
        self.localizer_velocity_previous = (self.pose.x, self.pose.y, self.pose.heading)
        self.localizer_velocity_elapsed = self.localizer_yaw_delta = 0.

    def state(self):
        positions = self.positions()
        return {'address': self.address, 'revision': 'MK2' if self.has_imu else 'MK1', 'firmware_version': '3.1.0',
                'status': self.status, 'has_imu': self.has_imu, 'x_mm': self.pose.x, 'y_mm': self.pose.y,
                'heading_rad': self.pose.heading, 'vx_mm_s': self.vx, 'vy_mm_s': self.vy, 'yaw_rate_rad_s': self.yaw_rate,
                'channels': [{'port': str(i), 'name': self.children[str(i)].name if str(i) in self.children else None,
                              'position': positions[i], 'velocity': self.velocities[i],
                              'velocity_ticks_s': self.velocities[i] * 1000 / self.params[3][i],
                              'sample_interval_ms': self.params[3][i], 'mode': 'pwm' if self.pwm(i) else 'quadrature',
                              'direction': -1 if self.params[0] & (1 << i) else 1} for i in range(8)]}


class OctoQuadMK1(OctoQuad):
    kind = 'octoquad_mk1'
    display_name = 'OctoQuad MK1'


class OctoQuadMK2(OctoQuad):
    kind = 'octoquad_mk2'
    display_name = 'OctoQuad MK2'
    has_imu = True
    option_metadata = {
        'x_port': {'label': 'Localizer X encoder channel', 'choices': list(range(8))},
        'y_port': {'label': 'Localizer Y encoder channel', 'choices': list(range(8))},
        'x_ticks_per_mm': {'label': 'Localizer X resolution (ticks/mm)', 'min': .01},
        'y_ticks_per_mm': {'label': 'Localizer Y resolution (ticks/mm)', 'min': .01},
        'tcp_offset_x_mm': {'label': 'TCP → robot origin X offset (mm)'},
        'tcp_offset_y_mm': {'label': 'TCP → robot origin Y offset (mm)'},
        'imu_heading_scalar': {'label': 'IMU heading scalar', 'min': .01},
    }

    def __init__(self, name, port, x_port=0, y_port=1, x_ticks_per_mm=13.26291192,
                 y_ticks_per_mm=13.26291192, tcp_offset_x_mm=0, tcp_offset_y_mm=0, imu_heading_scalar=1):
        super().__init__(name, port)
        for key, value in [(55, x_port), (56, y_port)]:
            if type(value) is not int or not 0 <= value <= 7:
                raise ValueError('Localizer channel must be an integer from 0–7')
            self.params[key] = value
        if x_port == y_port:
            raise ValueError('OctoQuad localizer X and Y must use different channels')
        for key, value in [(50, x_ticks_per_mm), (51, y_ticks_per_mm), (52, tcp_offset_x_mm),
                           (53, tcp_offset_y_mm), (54, imu_heading_scalar)]:
            self.params[key] = number(value, 'Localizer parameter', positive=key in (50, 51, 54))
        self.saved_params = deepcopy(self.params)
        self.localizer_params = deepcopy(self.params)
