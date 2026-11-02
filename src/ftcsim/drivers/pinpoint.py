"""Pinpoint firmware-v3 registers and an ideal planar estimator."""
import math
import struct
from .base import number
from .encoder import Encoder
from .i2c import I2CDriver


class GoBildaPinpoint(I2CDriver):
    display_name = 'goBILDA Pinpoint'
    option_metadata = {'ticks_per_mm': {'label': 'Estimator resolution (ticks/mm)', 'min': 0.01}, 'x_offset_mm': {'label': 'Estimator X pod offset (mm)'}, 'y_offset_mm': {'label': 'Estimator Y pod offset (mm)'}}
    kind = 'pinpoint'
    address = 0x31
    child_ports = ('x', 'y')
    child_connections = {'x': 'encoder', 'y': 'encoder'}
    child_defaults = {'x': {'axis': 'x'}, 'y': {'axis': 'y'}}

    def __init__(self, name, port, ticks_per_mm=13.26291192, x_offset_mm=0, y_offset_mm=0):
        super().__init__(name, port)
        self.resolution = number(ticks_per_mm, 'ticks_per_mm', positive=True)
        self.offsets = [number(x_offset_mm, 'x_offset_mm'), number(y_offset_mm, 'y_offset_mm')]
        self.directions = [1, 1]
        self.previous = [0.0, 0.0]
        self.x = self.y = self.heading = 0.0
        self.vx = self.vy = self.yaw_rate = 0.0
        self.yaw_scalar = 1.0
        self.calibration = 0.0
        self.loop_us = 20000
        self.scope = list(range(3, 14))
        self.scope.remove(4)  # bulk is status, loop time, encoders, pose, velocity

    def attach(self, port, child):
        if not isinstance(child, Encoder):
            raise ValueError('Pinpoint inputs require Encoder drivers')
        super().attach(port, child)
        self.previous[self.child_ports.index(port)] = child.position

    @property
    def status(self):
        if self.calibration > 0:
            return 2
        fault = (4 if 'x' not in self.children else 0) | (8 if 'y' not in self.children else 0)
        return fault or 1

    def step(self, dt, motion):
        self.calibration = max(0, self.calibration - dt)
        self.loop_us = max(1, int(dt * 1e6))
        delta = []
        for index, axis in enumerate(self.child_ports):
            pod = self.children.get(axis)
            position = pod.position if pod else 0
            delta.append((position - self.previous[index]) * self.directions[index] / self.resolution)
            self.previous[index] = position
        dh = motion.angular_velocity * self.yaw_scalar * dt
        dx = delta[0] + self.offsets[0] * dh
        dy = delta[1] - self.offsets[1] * dh
        # Integrate a constant body twist on SE(2), including finite-angle turns.
        sinc = math.sin(dh) / dh if abs(dh) > 1e-9 else 1
        cosc = (1 - math.cos(dh)) / dh if abs(dh) > 1e-9 else dh / 2
        body_x, body_y = sinc * dx - cosc * dy, cosc * dx + sinc * dy
        c, s = math.cos(self.heading), math.sin(self.heading)
        self.x += c * body_x - s * body_y
        self.y += s * body_x + c * body_y
        mid = self.heading + dh / 2
        self.vx = (math.cos(mid) * dx - math.sin(mid) * dy) / dt if dt else 0
        self.vy = (math.sin(mid) * dx + math.cos(mid) * dy) / dt if dt else 0
        self.heading = (self.heading + dh + math.pi) % (2 * math.pi) - math.pi
        self.yaw_rate = motion.angular_velocity * self.yaw_scalar

    def reset(self):
        self.x = self.y = self.heading = self.vx = self.vy = self.yaw_rate = 0.0
        for axis in self.child_ports:
            if axis in self.children:
                self.children[axis].reset()
        self.previous = [0.0, 0.0]

    def register(self, register):
        integers = {1: 1, 2: 3, 3: self.status, 4: 0, 5: self.loop_us}
        for index, axis in enumerate(self.child_ports):
            integers[6 + index] = self.children[axis].ticks * self.directions[index] if axis in self.children else 0
            integers[6 + index] = (integers[6 + index] + 2**31) % 2**32 - 2**31
        if register in integers:
            return struct.pack('<i', integers[register])
        floats = {8: self.x, 9: self.y, 10: self.heading, 11: self.vx, 12: self.vy,
                  13: self.yaw_rate, 14: self.resolution, 15: self.offsets[0], 16: self.offsets[1],
                  17: self.yaw_scalar, 19: math.cos(self.heading / 2), 20: 0, 21: 0,
                  22: math.sin(self.heading / 2), 23: 0, 24: 0}
        if register not in floats:
            raise ValueError(f'Unsupported Pinpoint register {register}')
        return struct.pack('<f', floats[register])

    @staticmethod
    def crc(data):
        value = 0x90
        for byte in data:
            value ^= byte
            for _ in range(8):
                value = ((value << 1) ^ (0x31 if value & 0x80 else 0)) & 255
        return value

    def read(self, register, count):
        payload = b''.join(self.register(r) for r in self.scope) if register == 18 else self.register(register)
        if count == len(payload) + 1:
            payload += bytes([self.crc(payload)])
        if count > len(payload):
            raise ValueError('Invalid Pinpoint register read length')
        return payload[:count]

    def write(self, register, data):
        if register == 25:
            if not data or len(data) > 24 or len(set(data)) != len(data):
                raise ValueError('Invalid Pinpoint bulk scope')
            for r in data:
                self.register(r)
            self.scope = list(data)
            return
        if len(data) != 4:
            raise ValueError('Pinpoint registers require four bytes')
        if register == 4:
            control, = struct.unpack('<I', data)
            if control & 2:
                self.reset()
            if control & 3:
                self.calibration = .25
            for index, reverse, forward in [(0, 16, 32), (1, 4, 8)]:
                if control & reverse:
                    self.directions[index] = -1
                if control & forward:
                    self.directions[index] = 1
            return
        value = number(struct.unpack('<f', data)[0], 'Pinpoint register')
        if register in (14, 17) and value <= 0:
            raise ValueError('Resolution/yaw scalar must be positive')
        if register == 8:
            self.x = value
        elif register == 9:
            self.y = value
        elif register == 10:
            self.heading = (value + math.pi) % (2 * math.pi) - math.pi
        elif register == 14:
            self.resolution = value
        elif register in (15, 16):
            self.offsets[register - 15] = value
        elif register == 17:
            self.yaw_scalar = value
        else:
            raise ValueError(f'Read-only/unsupported Pinpoint register {register}')

    def failsafe(self):
        super().failsafe()
        self.vx = self.vy = self.yaw_rate = 0.0

    def state(self):
        return {'address': self.address, 'status': self.status, 'x_mm': self.x, 'y_mm': self.y,
                'heading_rad': self.heading, 'vx_mm_s': self.vx, 'vy_mm_s': self.vy,
                'yaw_rate_rad_s': self.yaw_rate, 'ticks_per_mm': self.resolution,
                'x_offset_mm': self.offsets[0], 'y_offset_mm': self.offsets[1],
                'yaw_scalar': self.yaw_scalar, 'firmware_version': 3}
