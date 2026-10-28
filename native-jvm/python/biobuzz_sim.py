#!/usr/bin/env python3
"""BioBuzz desktop runtime, Lynx interceptor, simple motor model and local dashboard."""
import argparse
import collections
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from lynx_server import HubState, LynxServer

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'biobuzz/robot.json').read_text())
ZERO = dict(left_stick_x=0, left_stick_y=0, right_stick_x=0, right_trigger=0,
            a=False, left_bumper=False, right_bumper=False)


def unpack(data, fmt):
    return struct.unpack('<'+fmt, data)[0]


class MovingHub(HubState):
    def __init__(self):
        super().__init__()
        self.positions = [0.0]*4
        self.velocities = [0.0]*4

    def power(self, port):
        if self.registers.get(('MotorChannelEnable', port), b'\x00') == b'\x00': return 0.0
        mode = self.registers.get(('MotorChannelMode', port), b'\x00\x01')[0]
        if mode in (1, 2):
            return max(-1, min(1, unpack(self.registers.get(('MotorTargetVelocity', port), b'\x00\x00'), 'h')/2800))
        return unpack(self.registers.get(('MotorConstantPower', port), b'\x00\x00'), 'h')/32767

    def advance(self, dt):
        for port in range(4):
            velocity = self.power(port)*2800
            mode = self.registers.get(('MotorChannelMode', port), b'\x00\x01')[0]
            if mode == 2:
                target = self.registers.get(('MotorTargetPosition', port), bytes(6))
                delta = unpack(target[:4], 'i')-self.positions[port]
                velocity = math.copysign(min(abs(velocity), abs(delta)/dt), delta) if dt else 0
            self.velocities[port] = velocity
            self.positions[port] += velocity*dt
            self.encoders[port] = int(self.positions[port])

    def dispatch(self, request):
        name = request['command'].rsplit('.', 1)[-1]
        data = bytes.fromhex(request['payload'])
        if name == 'LynxResetMotorEncoderCommand': self.positions[data[0]] = 0
        if name == 'LynxGetBulkInputDataCommand':
            return (struct.pack('<B4iB', self.digital_inputs, *self.encoders, 0)
                    + struct.pack('<4h', *(int(v) for v in self.velocities))
                    + struct.pack('<4H', *self.analog_inputs))
        if name == 'LynxIsMotorAtTargetCommand':
            target = self.registers.get(('MotorTargetPosition', data[0]), bytes(6))
            return bytes([abs(unpack(target[:4], 'i')-self.encoders[data[0]]) <= unpack(target[4:], 'H')])
        return super().dispatch(request)


class Simulation(LynxServer):
    def __init__(self, port):
        (ROOT/'build').mkdir(exist_ok=True)
        super().__init__(('127.0.0.1', port), ROOT/'build/biobuzz-wire.jsonl')
        self.modules = {1: MovingHub(), 2: MovingHub()}
        self.gamepad = dict(ZERO)
        self.desired = 'idle'
        self.runtime = dict(status='connecting', error='', elapsed=0)
        self.action = dict(id=0, name='')
        self.pose = dict(x=0., y=0., heading=0., vx=0., vy=0., omega=0.)
        self.events = collections.deque(maxlen=70)
        self.command_count = 0
        self.last_input = time.monotonic()
        self.last_runtime = 0
        self.running = True
        self.worker = threading.Thread(target=self.tick, daemon=True)
        self.worker.start()

    def exchange(self, request):
        with self.lock:
            response = super().exchange(request)
            self.command_count += 1
            command = request.get('command', '').rsplit('.', 1)[-1]
            if 'Set' in command or command == 'LynxFailSafeCommand' or response['status'] in ('error', 'nack'):
                self.events.appendleft(dict(time=round(time.time(), 3), module=request.get('module'),
                                            command=command, payload=request.get('payload'), status=response['status']))
            return response

    def stop_motors(self):
        for state in self.modules.values():
            state.dispatch(dict(command='LynxFailSafeCommand', payload=''))
            for port in range(4): state.registers['MotorTargetVelocity', port] = b'\x00\x00'

    def tick(self):
        before = time.monotonic()
        while self.running:
            now = time.monotonic()
            dt, before = min(now-before, .1), now
            with self.lock:
                if self.runtime.get('status') == 'running' and now-self.last_input > 2:
                    self.gamepad = dict(ZERO)
                    self.desired = 'stop'
                    self.stop_motors()
                if self.last_runtime and now-self.last_runtime > 2:
                    self.stop_motors()
                for state in self.modules.values(): state.advance(dt)
                p = self.modules[1]
                # The left motors are reversed in BioBuzz's actual Constants.java.
                lf, lr, rf, rr = -p.power(0), -p.power(1), p.power(2), p.power(3)
                forward = (lf+lr+rf+rr)*12
                strafe = (-lf+lr+rf-rr)*12
                omega = (-lf-lr+rf+rr)*.8
                heading = self.pose['heading']
                vx = forward*math.cos(heading)-strafe*math.sin(heading)
                vy = forward*math.sin(heading)+strafe*math.cos(heading)
                self.pose.update(x=self.pose['x']+vx*dt, y=self.pose['y']+vy*dt,
                                 heading=(heading+omega*dt)%(2*math.pi), vx=vx, vy=vy, omega=omega)
            time.sleep(.02)

    def control(self):
        return dict(devices=CONFIG['devices'], gamepad=self.gamepad, desired=self.desired,
                    action=self.action, pose=self.pose)

    def snapshot(self):
        devices = []
        for device in CONFIG['devices']:
            d = dict(device)
            state = self.modules[d['module']]
            port = d['port']
            if d['type'] == 'motor':
                d.update(power=state.power(port), encoder=state.encoders[port], velocity=state.velocities[port],
                         enabled=bool(state.registers.get(('MotorChannelEnable', port), b'\x00')[0]),
                         mode=state.registers.get(('MotorChannelMode', port), b'\x00\x01')[0])
            else:
                pulse = unpack(state.registers.get(('ServoPulseWidth', port), struct.pack('<H', 1500)), 'H')
                d.update(pulse=pulse, position=max(0, min(1, (pulse-600)/1800)),
                         enabled=bool(state.registers.get(('ServoEnable', port), b'\x00')[0]))
            devices.append(d)
        return dict(devices=devices, runtime=self.runtime, desired=self.desired,
                    gamepad=self.gamepad, pose=self.pose, events=list(self.events), commands=self.command_count,
                    source=CONFIG['source'], heartbeatAge=time.monotonic()-self.last_runtime if self.last_runtime else None)


class Api(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def send(self, status, data, kind='application/json'):
        if not isinstance(data, bytes): data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try: self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError): pass

    def do_GET(self):
        sim = self.server.sim
        path = urlsplit(self.path).path
        with sim.lock:
            if path == '/api/control': return self.send(200, sim.control())
            if path == '/api/state': return self.send(200, sim.snapshot())
        if path in ('/', '/index.html'):
            return self.send(200, (ROOT/'biobuzz/dashboard/index.html').read_bytes(), 'text/html; charset=utf-8')
        self.send(404, dict(error='Not found'))

    def do_POST(self):
        # Keep browser writes on this local origin; do not accept cross-origin control.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://'+self.headers.get('Host', ''):
            return self.send(403, dict(error='Origin mismatch'))
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length < 32768: raise ValueError('Invalid body size')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict): raise ValueError('Expected object')
            sim = self.server.sim
            with sim.lock:
                path = urlsplit(self.path).path
                if path == '/api/input':
                    for name in ZERO:
                        if name not in data: continue
                        if isinstance(ZERO[name], bool): sim.gamepad[name] = bool(data[name])
                        else:
                            value = float(data[name])
                            if not math.isfinite(value): raise ValueError('Non-finite input')
                            sim.gamepad[name] = max(0 if name.endswith('trigger') else -1, min(1, value))
                    sim.last_input = time.monotonic()
                elif path == '/api/control':
                    if data.get('desired') not in ('init', 'start', 'stop'): raise ValueError('Invalid lifecycle command')
                    sim.desired = data['desired'];sim.last_input = time.monotonic()
                    if sim.desired in ('init','stop'): sim.gamepad=dict(ZERO);sim.stop_motors()
                elif path == '/api/runtime':
                    sim.runtime=data;sim.last_runtime=time.monotonic()
                    if data.get('status') == 'error': sim.stop_motors()
                    if sim.desired == 'init' and data.get('status') in ('initialized','error'): sim.desired='idle'
                    if sim.desired == 'stop' and data.get('status') == 'stopped': sim.desired='idle'
                elif path == '/api/action':
                    if data.get('name') == 'turret':
                        position = float(data.get('position', .5))
                        if not math.isfinite(position) or not 0 <= position <= 1: raise ValueError('Invalid servo position')
                        sim.action = dict(id=sim.action['id']+1,name='turret',position=position)
                        return self.send(200, dict(ok=True))
                    if data.get('name') != 'shooter': raise ValueError('Unsupported action')
                    rpm = float(data.get('rpm', 0))
                    if not math.isfinite(rpm) or not 0 <= rpm <= 6000: raise ValueError('RPM outside 0..6000')
                    sim.action=dict(id=sim.action['id']+1,name='shooter',rpm=rpm)
                elif path == '/api/pose':
                    for name in ('x', 'y', 'heading'):
                        value = float(data[name])
                        if not math.isfinite(value): raise ValueError('Invalid pose')
                        sim.pose[name] = value
                else: return self.send(404, dict(error='Not found'))
                return self.send(200, dict(ok=True))
        except (ValueError, KeyError, TypeError) as error: self.send(400, dict(error=str(error)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8085)
    parser.add_argument('--lynx-port', type=int, default=9015)
    parser.add_argument('--no-build', action='store_true')
    args = parser.parse_args()
    if not args.no_build:
        subprocess.run([str(ROOT.parent/'gradlew'), '-p', str(ROOT), 'writeClasspath', '--console=plain'], check=True, cwd=ROOT.parent)
    classpath = (ROOT/'build/classpath.txt').read_text()
    sim = Simulation(args.lynx_port)
    http = ThreadingHTTPServer(('127.0.0.1', args.port), Api);http.sim = sim
    threading.Thread(target=sim.serve_forever, daemon=True).start()
    threading.Thread(target=http.serve_forever, daemon=True).start()
    child = subprocess.Popen(['java', '-cp', classpath, 'ftcsim.jvm.BioBuzzRunner', str(args.port), str(args.lynx_port)], cwd=ROOT)
    print(f'BioBuzz simulator: http://127.0.0.1:{args.port}', flush=True)
    print('Open the dashboard, then INIT and START. Ctrl-C stops the runtime.', flush=True)
    try:
        while child.poll() is None: time.sleep(.2)
        raise RuntimeError(f'JVM runner exited with status {child.returncode}')
    except KeyboardInterrupt: pass
    finally:
        with sim.lock: sim.desired='stop';sim.stop_motors()
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: child.kill();child.wait()
        sim.running=False
        sim.shutdown();http.shutdown();sim.server_close();http.server_close()


if __name__ == '__main__': main()
