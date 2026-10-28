"""Real WebSocket and SDK integration tests; Java sources remain exclusively in sdk/."""
import asyncio
import json
import os
from pathlib import Path
import socket
import struct
import unittest
from contextlib import suppress
from aiohttp import ClientSession, WSServerHandshakeError
from aiohttp.test_utils import TestServer
from server import create_app, ROBOT, PEER
from physics.model import Robot

ROOT = Path(__file__).resolve().parents[2]


def command(name, payload='', module=1, response=False):
    return dict(version=1, type='lynx', id=1, module=module,
                command='com.qualcomm.hardware.lynx.commands.core.' + name,
                payload=payload, response='Response' if response else None)


class ModelTests(unittest.TestCase):
    def test_motor_speed_encoder_and_reset(self):
        robot = Robot()
        robot.exchange(command('LynxSetMotorConstantPowerCommand', '00ff7f'))
        robot.exchange(command('LynxSetMotorChannelEnableCommand', '0001'))
        robot.advance(.1)
        self.assertEqual(robot.hubs[1].encoders[0], 280)
        self.assertEqual(robot.hubs[1].velocities[0], 2800)
        robot.exchange(command('LynxResetMotorEncoderCommand', '00'))
        self.assertEqual(robot.hubs[1].encoders[0], 0)
        robot.failsafe(); robot.advance(.1)
        self.assertEqual(robot.hubs[1].encoders[0], 0)
        self.assertFalse(robot.hubs[1].enabled(0))

    def test_run_to_position_does_not_overshoot(self):
        robot = Robot()
        for name, payload in [('MotorChannelEnable','0001'), ('MotorChannelMode','000201'),
                              ('MotorTargetVelocity','00f003'), ('MotorTargetPosition','00'+struct.pack('<iH', 50, 1).hex())]:
            self.assertEqual(robot.exchange(command('LynxSet'+name+'Command',payload))['status'],'ack')
        robot.advance(.1)
        self.assertEqual(robot.hubs[1].encoders[0],50)
        robot.advance(.1)
        self.assertEqual(robot.hubs[1].velocities[0],0)

    def test_isolation_nack_and_invalid_payload(self):
        robot = Robot()
        robot.exchange(command('LynxSetMotorConstantPowerCommand','00ff7f'))
        self.assertEqual(robot.exchange(command('LynxGetMotorConstantPowerCommand','00',module=2,response=True))['payload'],'0000')
        self.assertEqual(robot.exchange(command('Unknown'))['status'],'nack')
        self.assertEqual(robot.exchange(command('LynxGetMotorEncoderPositionCommand','ff',response=True))['status'],'error')
        self.assertEqual(robot.exchange(command('LynxSetMotorConstantPowerCommand','xyz'))['status'],'error')


class HttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_static_ds_and_websocket_hardware_endpoint(self):
        server = TestServer(create_app()); await server.start_server()
        try:
            async with ClientSession() as client:
                async with client.get(server.make_url('/ds')) as response:
                    self.assertIn('FTC Desktop Driver Station', await response.text())
                async with client.post(server.make_url('/api/control'), json={}) as response:
                    self.assertEqual(response.status,404)
                async with client.ws_connect(server.make_url('/sim')) as ws:
                    await ws.send_json(command('LynxSetMotorConstantPowerCommand','00ff7f'))
                    self.assertEqual((await ws.receive_json())['status'],'ack')
                    with self.assertRaises(WSServerHandshakeError):
                        await client.ws_connect(server.make_url('/sim'))
                await asyncio.sleep(.05)
                self.assertFalse(server.app[ROBOT].connected)
                self.assertFalse(server.app[ROBOT].hubs[1].enabled(0))
        finally:
            await server.close()


class SdkHarness(unittest.IsolatedAsyncioTestCase):
    classpath_file = ROOT / 'sdk/runtime/build/classpath.txt'
    extra = []
    async def asyncSetUp(self):
        if not self.classpath_file.exists():
            self.skipTest('Build sdk/desktop :runtime:writeClasspath :biobuzz:writeClasspath first')
        self.server = TestServer(create_app()); await self.server.start_server()
        self.client = ClientSession()
        with socket.socket() as port:
            port.bind(('127.0.0.1',0)); self.ds_port = port.getsockname()[1]
        self.log_path = ROOT / 'sim' / 'tests' / '.sdk-test.log'
        self.log = self.log_path.open('w')
        self.process = await asyncio.create_subprocess_exec('java', '-Dftcsim.jvm=true', '-cp', self.classpath_file.read_text(),
            'ftcsim.jvm.DesktopSdk', '--sim', str(self.server.make_url('/sim')).replace('http:','ws:'),
            '--ds-port', str(self.ds_port), *self.extra, stdout=self.log, stderr=self.log)
        self.ws = None; self.pulse = None; self.inputs = ({}, {}); self.only_heartbeat = False
        self.addAsyncCleanup(self.cleanup)
        for _ in range(150):
            if self.process.returncode is not None:
                self.fail('SDK failed to start: ' + self.log_path.read_text())
            try:
                self.ws = await self.client.ws_connect(f'http://127.0.0.1:{self.ds_port}/ds', origin=str(self.server.make_url('')).rstrip('/'))
                break
            except (OSError, WSServerHandshakeError):
                await asyncio.sleep(.05)
        if self.ws is None: self.fail('SDK startup timeout: '+self.log_path.read_text())
        self.hello = await self.wait_for(lambda m:m.get('type')=='hello')
        self.identifier = 100
        async def pulse():
            while True:
                if self.only_heartbeat: await self.ws.send_json(dict(type='heartbeat'))
                else: await self.ws.send_json(dict(type='gamepads',gamepad1=self.inputs[0],gamepad2=self.inputs[1]))
                await asyncio.sleep(.08)
        self.pulse = asyncio.create_task(pulse())

    async def cleanup(self):
        if self.pulse:
            self.pulse.cancel()
            with suppress(asyncio.CancelledError, ConnectionError): await self.pulse
        if self.ws: await self.ws.close()
        if self.process.returncode is None:
            self.process.terminate()
            try: await asyncio.wait_for(self.process.wait(),5)
            except asyncio.TimeoutError:
                self.process.kill(); await self.process.wait()
        self.log.close(); await self.client.close(); await self.server.close()

    async def wait_for(self, predicate, timeout=6):
        async def receive():
            while True:
                data = await self.ws.receive_json()
                if predicate(data): return data
        try: return await asyncio.wait_for(receive(),timeout)
        except asyncio.TimeoutError:
            self.fail('Timed out waiting for SDK message. Log: '+self.log_path.read_text())

    async def send(self, kind, expected='ack', **fields):
        self.identifier += 1
        await self.ws.send_json(dict(type=kind,id=self.identifier,**fields))
        reply = await self.wait_for(lambda m:m.get('id')==self.identifier)
        self.assertEqual(reply['type'],expected,reply)
        return reply

    async def physical(self, predicate, timeout=4):
        for _ in range(int(timeout/.025)):
            snapshot = self.server.app[ROBOT].snapshot()
            if predicate(snapshot): return snapshot
            await asyncio.sleep(.025)
        self.fail('Physical state did not match: '+str(snapshot)+'\n'+self.log_path.read_text())


class SdkTests(SdkHarness):
    async def test_real_sdk_gamepads_motors_telemetry_and_linear_lifecycle(self):
        self.assertTrue(self.server.app[ROBOT].connected)  # Established before INIT.
        self.assertEqual(len(self.hello['opmodes']),2)
        await self.send('init')
        await self.send('select', expected='error', name='Linear motor demo')
        await self.send('start')
        self.inputs = (dict(a=True),dict(a=True))
        await self.physical(lambda s:s['motors'][0]['encoder']>100)
        telemetry = await self.wait_for(lambda m:m.get('type')=='telemetry' and 'gamepad2_a' in str(m))
        self.assertIn('true', str(telemetry).lower())
        await self.send('stop')
        await self.physical(lambda s:all(not m['enabled'] for m in s['motors']))
        await self.send('select', name='Linear motor demo')
        self.inputs=({},{}); await self.send('init'); await self.send('start')
        self.inputs=(dict(a=True),{})
        await self.physical(lambda s:s['motors'][0]['speed']>100)
        await self.send('stop')
        await self.physical(lambda s:all(not m['enabled'] for m in s['motors']))

    async def test_shutdown_with_active_opmode_disables_hardware(self):
        await self.send('init'); await self.send('start'); self.inputs=(dict(a=True),{})
        await self.physical(lambda s:s['motors'][0]['speed']>100)
        self.pulse.cancel()
        with suppress(asyncio.CancelledError): await self.pulse
        self.process.terminate()
        await asyncio.wait_for(self.process.wait(), 4)
        await self.physical(lambda s:not s['connected'] and all(not m['enabled'] for m in s['motors']))

    async def test_configuration_shared_socket_and_disconnect_failsafe(self):
        devices=[dict(name='motor',type='motor',module=2,port=1),dict(name='other',type='motor',module=1,port=0),dict(name='servo',type='servo',module=2,port=0)]
        await self.send('configure',devices=devices)
        await self.send('configure',expected='error',devices=devices+[devices[0]])
        await self.send('init'); await self.send('start'); self.inputs=(dict(a=True),{})
        await self.physical(lambda s:any(m['module']==2 and m['port']==1 and m['encoder']>100 for m in s['motors']))
        self.assertEqual(len(self.server.app[ROBOT].hubs),2)
        await self.ws.close()
        await self.physical(lambda s:all(not m['enabled'] for m in s['motors']))
        self.assertTrue(self.server.app[ROBOT].connected)

    async def test_stale_gamepads_heartbeat_and_simulator_loss(self):
        await self.send('init'); await self.send('start'); self.inputs=(dict(a=True),{})
        await self.physical(lambda s:s['motors'][0]['speed']>100)
        self.only_heartbeat=True
        await self.physical(lambda s:all(m['power']==0 for m in s['motors']))
        self.inputs=(dict(a=True),{}); self.only_heartbeat=False
        await self.physical(lambda s:s['motors'][0]['speed']>100)
        self.pulse.cancel()
        with suppress(asyncio.CancelledError): await self.pulse
        await self.wait_for(lambda m:m.get('type')=='status' and m.get('state')=='stopped')
        await self.physical(lambda s:all(not m['enabled'] for m in s['motors']))
        await self.server.app[PEER].socket.close()
        await self.wait_for(lambda m:m.get('type')=='status' and m.get('state')=='error')
        await self.send('init',expected='error')


class BioBuzzTests(SdkHarness):
    classpath_file = ROOT / 'sdk/examples/biobuzz/build/classpath.txt'
    extra = ['--config',str(ROOT/'sdk/examples/biobuzz/robot.json'), '--opmode','org.firstinspires.ftc.teamcode.opmodes.Tele']
    async def test_biobuzz_snapshot_runs_without_pose_backend(self):
        self.assertEqual(len(self.hello['devices']),12)
        await self.send('init'); await self.send('start')
        self.inputs=(dict(a=True,left_stick_y=-.6,right_trigger=.8),{})
        await self.physical(lambda s:any(m['module']==2 and m['port']==0 and m['speed']>100 for m in s['motors']))
        await self.physical(lambda s:any(m['module']==1 and abs(m['speed'])>100 for m in s['motors']))
        self.inputs=({}, {})
        await self.physical(lambda s:all(abs(m['power'])<.01 for m in s['motors'] if m['module']==2 and m['port'] in (0,1)))
        await self.send('stop')
        await self.physical(lambda s:all(not m['enabled'] for m in s['motors']))


if __name__ == '__main__': unittest.main()
