import json
import socket
import struct
import subprocess
import threading
import unittest
from pathlib import Path
from lynx_server import LynxServer


def request(name, payload='', module=1, response=True, identifier=1):
    return dict(version=1, id=identifier, module=module,
                command='com.qualcomm.hardware.lynx.commands.core.' + name,
                payload=payload, response='sdk.Response' if response else None)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = LynxServer(('127.0.0.1', 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def test_register_roundtrip_and_module_isolation(self):
        reply = self.server.exchange(request('LynxSetMotorConstantPowerCommand', '000040', response=False))
        self.assertEqual(reply['status'], 'ack')
        self.assertEqual(self.server.exchange(request('LynxGetMotorConstantPowerCommand', '00'))['payload'], '0040')
        self.assertEqual(self.server.exchange(request('LynxGetMotorConstantPowerCommand', '00', module=2))['payload'], '0000')

    def test_installed_distribution(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([str(root/'build/install/ftcsim/bin/ftcsim'), str(self.server.server_address[1])],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('JVM -> Python -> SDK OK', result.stdout)

    def test_unknown_command_is_nack(self):
        self.assertEqual(self.server.exchange(request('UnknownCommand'))['reason'], 255)

    def test_bad_payload_is_error(self):
        self.assertEqual(self.server.exchange(request('LynxSetMotorConstantPowerCommand', 'ff'))['status'], 'error')
        self.assertEqual(self.server.exchange(request('LynxGetADCCommand', 'zz'))['status'], 'error')

    def test_fragmented_frames(self):
        with socket.create_connection(self.server.server_address, timeout=2) as connection:
            data = json.dumps(request('LynxGetMotorEncoderPositionCommand', '00')).encode()
            frame = struct.pack('!I', len(data)) + data
            for b in frame: connection.sendall(bytes([b]))
            stream = connection.makefile('rb')
            size, = struct.unpack('!I', stream.read(4))
            self.assertEqual(json.loads(stream.read(size))['payload'], '00000000')
            stream.close()

    def test_oversized_frame_disconnects(self):
        with socket.create_connection(self.server.server_address, timeout=2) as connection:
            connection.sendall(struct.pack('!I', 1024 * 1024 + 1))
            self.assertEqual(connection.recv(1), b'')

    def test_interceptor_receives_set_and_get(self):
        seen = []
        def interceptor(req, state):
            seen.append(req['command'])
            if req['command'].endswith('LynxGetMotorEncoderPositionCommand'):
                return struct.pack('<i', 4321)
        self.server.interceptor = interceptor
        self.server.exchange(request('LynxSetMotorConstantPowerCommand', '000040', response=False))
        reply = self.server.exchange(request('LynxGetMotorEncoderPositionCommand', '00'))
        self.assertEqual(reply['payload'], struct.pack('<i', 4321).hex())
        self.assertEqual(len(seen), 2)

    def test_jvm_nack_and_malformed_reply(self):
        root = Path(__file__).resolve().parents[1]
        for mode in ('nack', 'malformed'):
            with self.subTest(mode=mode):
                def interceptor(req, state):
                    if mode == 'nack': raise NotImplementedError()
                    return b''  # Too short for the real SDK power response decoder.
                self.server.interceptor = interceptor
                result = subprocess.run(['java', '-cp', (root/'build/classpath.txt').read_text(),
                                         'ftcsim.jvm.ProtocolSmokeTest', str(self.server.server_address[1]), mode],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Expected ' + mode + ' handled', result.stdout)

    def test_jvm_sdk_end_to_end(self):
        root = Path(__file__).resolve().parents[1]
        cp = root/'build/classpath.txt'
        self.assertTrue(cp.exists(), 'Run ./gradlew :simulator:writeClasspath first')
        # Run outside Gradle/Android and make Python's response observably different.
        seen = []
        def interceptor(req, state):
            seen.append(req['command'].rsplit('.', 1)[-1])
            if seen[-1] == 'LynxGetMotorEncoderPositionCommand': return struct.pack('<i', 4321)
        self.server.interceptor = interceptor
        result = subprocess.run(['java', '-cp', cp.read_text(), 'ftcsim.jvm.SmokeTest', str(self.server.server_address[1])],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('encoder=4321', result.stdout)
        self.assertIn('LynxSetMotorConstantPowerCommand', seen)
        self.assertIn('LynxGetMotorConstantPowerCommand', seen)


    def test_team_facing_motor_servo_and_bulk_api(self):
        root = Path(__file__).resolve().parents[1]
        seen = []
        def interceptor(req, state):
            seen.append(req['command'].rsplit('.', 1)[-1])
        self.server.interceptor = interceptor
        result = subprocess.run(['java', '-cp', (root/'build/classpath.txt').read_text(),
                                 'ftcsim.jvm.ControllerSmokeTest', str(self.server.server_address[1])],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('SDK devices -> Python OK', result.stdout)
        self.assertIn('LynxGetMotorConstantPowerCommand', seen)
        self.assertIn('LynxSetServoPulseWidthCommand', seen)
        self.assertIn('LynxGetBulkInputDataCommand', seen)


if __name__ == '__main__': unittest.main()
