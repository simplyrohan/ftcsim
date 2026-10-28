"""Base register-addressed I2C device and Lynx I2C bus transport."""
from .base import Driver


class I2CDriver(Driver):
    connection = 'i2c'
    address = 0

    def __init__(self, name, port):
        super().__init__(name, port)
        self.pointer = 0

    def read(self, register, count):
        raise NotImplementedError('I2C read')

    def write(self, register, data):
        raise NotImplementedError('I2C write')


class I2CBus:
    def __init__(self):
        self.devices = {}
        self.pending_read = b''
        self.read_status = 0
        self.written = 0
        self.write_status = 0

    def attach(self, device):
        if device.address in self.devices:
            raise ValueError('I2C address already occupied')
        self.devices[device.address] = device

    def handle_lynx(self, name, data):
        # Hub has already removed the bus byte and validated its range.
        if name == 'LynxI2cConfigureChannelCommand':
            if len(data) != 1 or data[0] > 2:
                raise ValueError('Invalid I2C speed')
            return b''
        if name == 'LynxI2cReadStatusQueryCommand':
            if data:
                raise ValueError('Unexpected I2C status payload')
            return bytes([self.read_status, len(self.pending_read)]) + self.pending_read
        if name == 'LynxI2cWriteStatusQueryCommand':
            if data:
                raise ValueError('Unexpected I2C status payload')
            return bytes([self.write_status, self.written])
        if not data or data[0] > 127:
            raise ValueError('Invalid I2C address')
        device = self.devices.get(data[0])
        data = data[1:]
        if name in ('LynxI2cWriteMultipleBytesCommand', 'LynxI2cWriteSingleByteCommand'):
            if name == 'LynxI2cWriteMultipleBytesCommand':
                if not data or not 1 <= data[0] <= 100 or len(data) != data[0] + 1:
                    raise ValueError('Invalid I2C write length')
                data = data[1:]
            elif len(data) != 1:
                raise ValueError('Invalid I2C single write')
            self.written = len(data)
            self.write_status = 0 if device else 1
            if device:
                device.pointer = data[0]
                if len(data) > 1:
                    device.write(data[0], data[1:])
            return b''
        if name in ('LynxI2cWriteReadMultipleBytesCommand', 'LynxI2cReadMultipleBytesCommand', 'LynxI2cReadSingleByteCommand'):
            expected = 2 if 'WriteRead' in name else (0 if 'Single' in name else 1)
            if len(data) != expected:
                raise ValueError('Invalid I2C read payload')
            count = data[0] if data else 1
            if not 1 <= count <= 100:
                raise ValueError('Invalid I2C read length')
            self.read_status = 0 if device else 1
            if device:
                if 'WriteRead' in name:
                    device.pointer = data[1]
                self.pending_read = device.read(device.pointer, count)
                if len(self.pending_read) != count:
                    raise ValueError('I2C driver returned incorrect read length')
            else:
                self.pending_read = bytes(count)
            return b''
        raise NotImplementedError(name)
