#!/usr/bin/env python3
"""Loopback Lynx command interceptor. Standard library only; no USB or Android.

Frames: 4-byte big-endian length, followed by UTF-8 JSON. Payloads are hex
encoded SDK payload bytes (little-endian fields). Unknown commands NACK 255.
"""
import argparse
import importlib.util
import json
import socketserver
import struct
import threading
from dataclasses import dataclass, field
from pathlib import Path

MAX_FRAME = 1024 * 1024


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


class LynxServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, log_path=None, interceptor=None):
        if address[0] != '127.0.0.1': raise ValueError('Only IPv4 loopback is supported')
        super().__init__(address, Handler)
        self.lock = threading.RLock()
        self.modules = {}
        self.interceptor = interceptor
        self.log = open(log_path, 'a', encoding='utf-8') if log_path else None

    def exchange(self, request):
        with self.lock:
            identifier = request.get('id')
            try:
                if request.get('version') != 1: raise ValueError('Unsupported protocol version')
                module = request['module']
                if type(module) is not int or not 1 <= module <= 254: raise ValueError('Invalid module address')
                if type(identifier) is not int: raise ValueError('Invalid request ID')
                if not isinstance(request['command'], str) or not isinstance(request['payload'], str): raise ValueError('Invalid command/payload')
                bytes.fromhex(request['payload'])
                state = self.modules.setdefault(module, HubState())
                payload = self.interceptor(request, state) if self.interceptor else None
                if payload is None: payload = state.dispatch(request)
                if not isinstance(payload, bytes): raise TypeError('Interceptor must return bytes or None')
                response = {'id': identifier, 'status': 'response' if request.get('response') else 'ack', 'payload': payload.hex()}
            except NotImplementedError:
                response = {'id': identifier, 'status': 'nack', 'reason': 255}
            except (ValueError, KeyError, IndexError, TypeError, struct.error) as error:
                response = {'id': identifier, 'status': 'error', 'message': str(error)}
            except Exception as error:
                response = {'id': identifier, 'status': 'error', 'message': 'Interceptor failed: ' + str(error)}
            if self.log:
                self.log.write(json.dumps({'request': request, 'reply': response}) + '\n')
                self.log.flush()
            return response

    def server_close(self):
        super().server_close()
        if self.log: self.log.close()


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(30)
        try:
            while True:
                header = self.rfile.read(4)
                if not header: return
                if len(header) != 4: return
                size, = struct.unpack('!I', header)
                if not 0 < size <= MAX_FRAME: return
                data = self.rfile.read(size)
                if len(data) != size: return
                request = json.loads(data)
                if not isinstance(request, dict): return
                response = json.dumps(self.server.exchange(request)).encode('utf-8')
                if len(response) > MAX_FRAME: return
                self.wfile.write(struct.pack('!I', len(response)) + response)
                self.wfile.flush()
        except (OSError, ValueError, UnicodeError):
            return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=9010)
    parser.add_argument('--log', type=Path, help='Append every intercepted request and reply as JSONL')
    parser.add_argument('--handler', type=Path, help='Python file defining handle(request, state) -> bytes | None')
    args = parser.parse_args()
    interceptor = None
    if args.handler:
        spec = importlib.util.spec_from_file_location('lynx_interceptor', args.handler)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        interceptor = module.handle
    with LynxServer(('127.0.0.1', args.port), args.log, interceptor) as server:
        print(f'Lynx interceptor listening on 127.0.0.1:{server.server_address[1]}', flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass


if __name__ == '__main__': main()
