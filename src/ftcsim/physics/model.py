"""Hub protocol routing and physical driver topology. No OpMode/DS lifecycle."""
import struct
from copy import deepcopy
from .registers import HubState
from ..drivers import BodyMotion, DCMotor, Servo, Encoder, I2CDriver, DRIVERS
from ..drivers.base import number
from ..drivers.i2c import I2CBus
from ..mechanisms import MECHANISMS


class Hub(HubState):
    def __init__(self, address):
        super().__init__()
        self.address = address
        # Real SDK controllers initialize every channel, even unused channels.
        self.motors = [DCMotor(f'hub{address}:motor{i}', i) for i in range(4)]
        self.servos = [Servo(f'hub{address}:servo{i}', i) for i in range(6)]
        self.encoder_inputs = list(self.motors)
        self.buses = [I2CBus() for _ in range(4)]
        self.devices = []
        self.connections = set()

    def attach(self, device):
        connection, port = device.connection, device.port
        slots = {(connection, port)}
        if isinstance(device, DCMotor):
            slots.add(('encoder', port))
        if slots & self.connections:
            raise ValueError(f'Hub {self.address}: occupied {connection} port {port}')
        self.connections.update(slots)
        if isinstance(device, DCMotor):
            self.motors[port] = device
            self.encoder_inputs[port] = device
        elif isinstance(device, Encoder):
            self.encoder_inputs[port] = device
        elif isinstance(device, Servo):
            self.servos[port] = device
        elif isinstance(device, I2CDriver):
            self.buses[port].attach(device)
        else:
            raise ValueError(f'Unsupported hub connection: {connection}')
        self.devices.append(device)

    @property
    def root_drivers(self):
        # Include hidden hardware channels initialized by SDK controllers.
        return tuple(dict.fromkeys([*self.motors, *self.servos, *self.devices]))

    def failsafe(self):
        for device in self.root_drivers:
            device.failsafe()

    def dispatch(self, request):
        name = request['command'].rsplit('.', 1)[-1]
        data = bytes.fromhex(request['payload'])
        if name == 'LynxFailSafeCommand':
            if data:
                raise ValueError('Unexpected failsafe payload')
            self.failsafe()
            return b''
        if name == 'LynxGetBulkInputDataCommand':
            if data:
                raise ValueError('Unexpected bulk payload')
            encoders = [encoder.ticks for encoder in self.encoder_inputs]
            velocities = [max(-32768, min(32767, int(encoder.velocity))) for encoder in self.encoder_inputs]
            return struct.pack('<B4iB4h4H', self.digital_inputs, *encoders, 0, *velocities, *self.analog_inputs)
        if name.startswith('LynxI2c'):
            if not data or data[0] >= 4:
                raise ValueError('Invalid I2C bus')
            return self.buses[data[0]].handle_lynx(name, data[1:])
        if 'Motor' in name:
            if not data or data[0] >= 4:
                raise ValueError('Invalid motor port')
            port, payload = data[0], data[1:]
            if name in ('LynxResetMotorEncoderCommand', 'LynxGetMotorEncoderPositionCommand', 'LynxIsMotorAtTargetCommand'):
                if payload:
                    raise ValueError('Unexpected encoder payload')
                if name == 'LynxResetMotorEncoderCommand':
                    self.encoder_inputs[port].reset()
                    return b''
                if name == 'LynxGetMotorEncoderPositionCommand':
                    return struct.pack('<i', self.encoder_inputs[port].ticks)
                return bytes([self.motors[port].at_target])
            return self.motors[port].handle_lynx(name, payload)
        if 'Servo' in name:
            if not data or data[0] >= 6:
                raise ValueError('Invalid servo port')
            return self.servos[data[0]].handle_lynx(name, data[1:])
        return super().dispatch(request)

    def snapshot(self):
        return [dict(device.snapshot(), module=self.address) for device in self.devices]


class Robot:
    def __init__(self):
        self.hubs = {}
        self.command_count = 0
        self.connected = False
        self.motion = BodyMotion()
        self.mechanisms = []
        self.mechanism_configuration = []
        self.mechanism_error = ''

    @staticmethod
    def driver_index(hubs):
        result = {}
        def visit(driver):
            result[driver.name] = driver
            for child in driver.children.values():
                visit(child)
        for hub in hubs.values():
            for driver in hub.devices:
                visit(driver)
        return result

    def configure_mechanisms(self, definitions):
        instances = MECHANISMS.create_all(definitions, self.driver_index(self.hubs))
        self.mechanisms = instances
        self.mechanism_configuration = deepcopy(definitions)
        self.mechanism_error = ''

    def configure(self, devices, *, validate_only=False):
        if not isinstance(devices, list) or len(devices) > 256:
            raise ValueError('Expected a list of at most 256 devices')
        hubs, names = {}, set()
        for definition in devices:
            if not isinstance(definition, dict):
                raise ValueError('Expected a device object')
            address = definition.get('module')
            if type(address) is not int or not 1 <= address <= 254:
                raise ValueError('Invalid hub address')
            driver = DRIVERS.create(definition, names)
            if address not in hubs:
                hubs[address] = Hub(address)
            hubs[address].attach(driver)
        # Construct/validate everything before replacing live state.
        if validate_only:
            return
        self.failsafe()
        self.hubs = hubs
        # Mechanisms never constrain the SDK's hardware map. Rebind to replacement
        # drivers, or suspend the model with a visible error if a reference vanished.
        try:
            self.mechanisms = MECHANISMS.create_all(self.mechanism_configuration, self.driver_index(hubs))
            self.mechanism_error = ''
        except (ValueError, TypeError) as error:
            self.mechanisms = []
            self.mechanism_error = f'Mechanisms suspended after hardware change: {error}'

    def set_motion(self, vx=0, vy=0, angular_velocity=0):
        values = [number(value, label) for value, label in [(vx, 'vx'), (vy, 'vy'), (angular_velocity, 'angular_velocity')]]
        if any(abs(value) > limit for value, limit in zip(values, [10000, 10000, 100])):
            raise ValueError('Motion input exceeds 10000 mm/s or 100 rad/s')
        self.motion = BodyMotion(*values)

    def failsafe(self):
        self.motion = BodyMotion()
        for hub in self.hubs.values():
            hub.failsafe()
        for mechanism in self.mechanisms:
            mechanism.failsafe()

    def exchange(self, request):
        identifier = request.get('id')
        kind = request.get('type')
        try:
            if request.get('version') != 1 or type(identifier) is not int:
                raise ValueError('Expected protocol version 1 and integer id')
            if kind == 'configure':
                validate_only = request.get('validateOnly', False)
                if type(validate_only) is not bool:
                    raise ValueError('validateOnly must be a boolean')
                self.configure(request['devices'], validate_only=validate_only)
                return dict(type=kind, id=identifier, status='ack', payload='')
            if kind != 'lynx':
                raise ValueError('Expected Lynx or configuration request')
            address = request['module']
            if type(address) is not int or not 1 <= address <= 254:
                raise ValueError('Invalid module')
            if not isinstance(request['command'], str) or not isinstance(request['payload'], str):
                raise ValueError('Expected command and hex payload strings')
            bytes.fromhex(request['payload'])
            if address not in self.hubs:
                raise ValueError(f'Hub {address} is not configured')
            payload = self.hubs[address].dispatch(request)
            if request['command'].rsplit('.', 1)[-1] == 'LynxFailSafeCommand':
                self.motion = BodyMotion()
                for mechanism in self.mechanisms:
                    mechanism.failsafe()
            self.command_count += 1
            return dict(type=kind, id=identifier, status='response' if request.get('response') else 'ack', payload=payload.hex())
        except NotImplementedError:
            return dict(type=kind, id=identifier, status='nack', reason=255)
        except (ValueError, KeyError, TypeError, IndexError, struct.error) as error:
            return dict(type=kind, id=identifier, status='error', message=str(error))

    def advance(self, dt):
        dt = number(dt, 'dt')
        if dt < 0:
            raise ValueError('dt must be non-negative')
        roots = [driver for hub in self.hubs.values() for driver in hub.root_drivers]
        # Global phases avoid a one-tick delay and hub-order dependence. Motors
        # advance first; mechanisms read velocity; pods advance before their IMU.
        for driver in roots:
            if driver.phase == 'actuator':
                driver.advance(dt, self.motion)
        sensor_inputs = {}
        for mechanism in self.mechanisms:
            mechanism.advance(dt)
            sensor_inputs.update(mechanism.sensor_inputs())
        for driver in roots:
            if driver.phase == 'sensor':
                driver.advance(dt, sensor_inputs.get(driver, self.motion))

    def snapshot(self):
        devices = [device for _, hub in sorted(self.hubs.items()) for device in hub.snapshot()]
        return dict(type='state', connected=self.connected, commands=self.command_count,
                    devices=devices, mechanisms=[mechanism.snapshot() for mechanism in self.mechanisms],
                    mechanism_configuration=deepcopy(self.mechanism_configuration),
                    mechanism_error=self.mechanism_error,
                    motion=dict(vx=self.motion.vx, vy=self.motion.vy,
                                               angular_velocity=self.motion.angular_velocity))
