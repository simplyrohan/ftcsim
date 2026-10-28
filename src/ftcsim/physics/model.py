"""Independent hub/motor model. No robot code, gamepads, lifecycle or localization."""
import math
import struct
from .registers import HubState


class MotorHub(HubState):
    MAX_TICKS_PER_SECOND = 2800

    def __init__(self):
        super().__init__()
        self.positions = [0.0] * 4
        self.velocities = [0.0] * 4

    def mode(self, port):
        return self.registers.get(('MotorChannelMode', port), b'\x00\x01')[0]

    def enabled(self, port):
        return bool(self.registers.get(('MotorChannelEnable', port), b'\x00')[0])

    def power(self, port):
        if not self.enabled(port):
            return 0.0
        if self.mode(port) in (1, 2):
            velocity, = struct.unpack('<h', self.registers.get(('MotorTargetVelocity', port), bytes(2)))
            return max(-1, min(1, velocity / self.MAX_TICKS_PER_SECOND))
        value, = struct.unpack('<h', self.registers.get(('MotorConstantPower', port), bytes(2)))
        return max(-1, min(1, value / 32767))

    def advance(self, dt):
        for port in range(4):
            velocity = self.power(port) * self.MAX_TICKS_PER_SECOND
            if self.mode(port) == 2:
                target, tolerance = struct.unpack('<iH', self.registers.get(('MotorTargetPosition', port), bytes(6)))
                delta = target - self.positions[port]
                velocity = (math.copysign(min(abs(velocity), abs(delta) / dt), delta)
                            if dt and abs(delta) > tolerance else 0)
            self.velocities[port] = velocity
            self.positions[port] += velocity * dt
            # Hub encoders are signed 32-bit counters.
            self.encoders[port] = (int(self.positions[port]) + 2**31) % 2**32 - 2**31

    def dispatch(self, request):
        name = request['command'].rsplit('.', 1)[-1]
        data = bytes.fromhex(request['payload'])
        if name in ('LynxResetMotorEncoderCommand', 'LynxGetMotorEncoderPositionCommand', 'LynxIsMotorAtTargetCommand'):
            if len(data) != 1 or data[0] >= 4:
                raise ValueError('Invalid motor port')
        if name == 'LynxResetMotorEncoderCommand':
            self.positions[data[0]] = 0
        if name == 'LynxGetBulkInputDataCommand':
            return (struct.pack('<B4iB', self.digital_inputs, *self.encoders, 0)
                    + struct.pack('<4h', *(int(v) for v in self.velocities))
                    + struct.pack('<4H', *self.analog_inputs))
        if name == 'LynxIsMotorAtTargetCommand':
            target, tolerance = struct.unpack('<iH', self.registers.get(('MotorTargetPosition', data[0]), bytes(6)))
            return bytes([abs(target - self.encoders[data[0]]) <= tolerance])
        return super().dispatch(request)

    def snapshot(self, address):
        return [dict(module=address, port=port, enabled=self.enabled(port), mode=self.mode(port),
                     power=self.power(port), speed=self.velocities[port], encoder=self.encoders[port])
                for port in range(4)]


class Robot:
    def __init__(self):
        self.hubs = {}
        self.command_count = 0
        self.connected = False

    def failsafe(self):
        for hub in self.hubs.values():
            hub.dispatch(dict(command='LynxFailSafeCommand', payload=''))
            hub.velocities = [0.0] * 4

    def exchange(self, request):
        identifier = request.get('id')
        try:
            if request.get('version') != 1 or request.get('type') != 'lynx':
                raise ValueError('Expected version 1 Lynx request')
            address = request['module']
            if type(identifier) is not int or type(address) is not int or not 1 <= address <= 254:
                raise ValueError('Invalid id or module')
            if not isinstance(request['command'], str) or not isinstance(request['payload'], str):
                raise ValueError('Expected command and hex payload strings')
            bytes.fromhex(request['payload'])
            payload = self.hubs.setdefault(address, MotorHub()).dispatch(request)
            self.command_count += 1
            return dict(type='lynx', id=identifier, status='response' if request.get('response') else 'ack', payload=payload.hex())
        except NotImplementedError:
            return dict(type='lynx', id=identifier, status='nack', reason=255)
        except (ValueError, KeyError, TypeError, IndexError, struct.error) as error:
            return dict(type='lynx', id=identifier, status='error', message=str(error))

    def advance(self, dt):
        for hub in self.hubs.values():
            hub.advance(dt)

    def snapshot(self):
        return dict(type='state', connected=self.connected, commands=self.command_count,
                    motors=[m for address, hub in sorted(self.hubs.items()) for m in hub.snapshot(address)])
