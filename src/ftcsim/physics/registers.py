"""Lynx register payloads shared with the SDK; numeric fields are little endian."""
import struct
from dataclasses import dataclass, field


@dataclass
class HubState:
    """Register state, not a physics simulator. One instance per module address."""
    registers: dict = field(default_factory=dict)
    encoders: list = field(default_factory=lambda: [0] * 4)
    digital_inputs: int = 0
    analog_inputs: list = field(default_factory=lambda: [0] * 4)
    led: bytes = b'\x00\x00\x00'

    def dispatch(self, request):
        name = request['command'].rsplit('.', 1)[-1]
        data = bytes.fromhex(request['payload'])
        # Set/get pairs preserve the actual wire bytes. Defaults match the
        # documented response widths; unsupported I2C and firmware calls NACK.
        pairs = {
            'MotorConstantPower': (2, b'\x00\x00'),
            'MotorChannelMode': (2, b'\x00\x01'),
            'MotorChannelEnable': (1, b'\x00'),
            'MotorChannelCurrentAlertLevel': (2, b'\xff\x7f'),
            'MotorTargetVelocity': (2, b'\x00\x00'),
            'MotorTargetPosition': (6, b'\x00' * 6),
            'ServoConfiguration': (2, struct.pack('<H', 20000)),
            'ServoPulseWidth': (2, struct.pack('<H', 1500)),
            'ServoEnable': (1, b'\x00'),
            'PWMConfiguration': (2, struct.pack('<H', 20000)),
            'PWMPulseWidth': (2, b'\x00\x00'),
            'PWMEnable': (1, b'\x00'),
            'DIODirection': (1, b'\x00'),
        }
        for suffix, (width, default) in pairs.items():
            if name in ('LynxSet' + suffix + 'Command', 'LynxGet' + suffix + 'Command'):
                ports = 4 if suffix.startswith(('Motor', 'PWM')) else (6 if suffix.startswith('Servo') else 8)
                if not data or data[0] >= ports: raise ValueError('Invalid channel')
            if name == 'LynxSet' + suffix + 'Command':
                if len(data) != width + 1: raise ValueError('Invalid set payload length')
                self.registers[suffix, data[0]] = data[1:]
                return b''
            if name == 'LynxGet' + suffix + 'Command':
                if len(data) != 1: raise ValueError('Invalid get payload length')
                return self.registers.get((suffix, data[0]), default)
        if name == 'LynxGetMotorEncoderPositionCommand':
            return struct.pack('<i', self.encoders[data[0]])
        if name == 'LynxResetMotorEncoderCommand':
            self.encoders[data[0]] = 0
            return b''
        if name == 'LynxIsMotorAtTargetCommand': return b'\x01'
        if name in ('LynxSetMotorPIDControlLoopCoefficientsCommand', 'LynxSetMotorPIDFControlLoopCoefficientsCommand'):
            width = 17 if 'PIDF' in name else 12
            if len(data) != width + 2: raise ValueError('Invalid PID payload')
            self.registers[name.replace('Set', 'Get'), data[:2]] = data[2:]
            return b''
        if name in ('LynxGetMotorPIDControlLoopCoefficientsCommand', 'LynxGetMotorPIDFControlLoopCoefficientsCommand'):
            width = 17 if 'PIDF' in name else 12
            return self.registers.get((name, data[:2]), b'\x00' * width)
        if name == 'LynxGetBulkInputDataCommand':
            return (struct.pack('<B4iB', self.digital_inputs, *self.encoders, 0)
                    + b'\x00' * 8 + struct.pack('<4H', *self.analog_inputs))
        if name == 'LynxGetSingleDIOInputCommand': return bytes([(self.digital_inputs >> data[0]) & 1])
        if name == 'LynxGetAllDIOInputsCommand': return bytes([self.digital_inputs])
        if name == 'LynxSetSingleDIOOutputCommand':
            self.digital_inputs = (self.digital_inputs & ~(1 << data[0])) | ((data[1] & 1) << data[0])
            return b''
        if name == 'LynxSetAllDIOOutputsCommand':
            self.digital_inputs = data[0]
            return b''
        if name == 'LynxGetADCCommand':
            # External inputs 0..3, battery monitor 12 V; other internal channels 0.
            value = self.analog_inputs[data[0]] if data[0] < 4 else (12000 if data[0] == 13 else (5000 if data[0] == 12 else 0))
            return struct.pack('<H', value)
        if name == 'LynxGetModuleStatusCommand': return b'\x00\x00'
        if name == 'LynxGetModuleLEDColorCommand': return self.led
        if name == 'LynxSetModuleLEDColorCommand':
            if len(data) != 3: raise ValueError('Invalid LED payload')
            self.led = data
            return b''
        if name == 'LynxReadVersionStringCommand':
            text = b'FTCSIM JVM 12.0.0'
            return bytes([len(text)]) + text
        if name == 'LynxPhoneChargeQueryCommand': return b'\x00'
        if name == 'LynxFailSafeCommand':
            for motor in range(4):
                self.registers['MotorConstantPower', motor] = b'\x00\x00'
                self.registers['MotorChannelEnable', motor] = b'\x00'
            for servo in range(6): self.registers['ServoEnable', servo] = b'\x00'
            return b''
        if name in ('LynxKeepAliveCommand', 'LynxFtdiResetControlCommand', 'LynxPhoneChargeControlCommand'):
            return b''
        raise NotImplementedError(name)
