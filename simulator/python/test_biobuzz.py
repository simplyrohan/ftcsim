"""Integration: copied Kotlin TeleOp -> real SDK -> TCP -> simulated hardware."""
import json
from pathlib import Path
import subprocess
import threading
import time
import unittest
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from biobuzz_sim import Simulation, Api, ROOT


class BioBuzzIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = Simulation(0)
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), Api)
        cls.http.sim = cls.sim
        cls.base = 'http://127.0.0.1:' + str(cls.http.server_address[1])
        for server in (cls.sim, cls.http): threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.log = open(ROOT/'build/biobuzz-test.log', 'w')
        cls.child = subprocess.Popen(['java', '-cp', (ROOT/'build/classpath.txt').read_text(),
                                     'ftcsim.jvm.BioBuzzRunner', str(cls.http.server_address[1]),
                                     str(cls.sim.server_address[1])], cwd=ROOT, stdout=cls.log, stderr=cls.log)
        cls.await_state(lambda s: s['runtime']['status'] == 'idle')

    @classmethod
    def tearDownClass(cls):
        cls.child.terminate()
        try: cls.child.wait(timeout=5)
        except subprocess.TimeoutExpired: cls.child.kill();cls.child.wait()
        cls.sim.running = False
        for server in (cls.sim, cls.http): server.shutdown();server.server_close()
        cls.log.close()

    @classmethod
    def request(cls, path, data=None):
        req = cls.base + path if data is None else Request(cls.base+path, json.dumps(data).encode(), {'Content-Type': 'application/json'})
        with urlopen(req, timeout=3) as stream: return json.load(stream)

    @classmethod
    def await_state(cls, predicate, timeout=6):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            state = cls.request('/api/state')
            if state['runtime']['status'] == 'error': raise AssertionError(state['runtime']['error'])
            if predicate(state): return state
            time.sleep(.04)
        raise AssertionError('Timed out: '+json.dumps(state['runtime']))

    def setUp(self):
        self.request('/api/control', {'desired':'init'})
        self.await_state(lambda s:s['runtime']['status']=='initialized')
        self.request('/api/control', {'desired':'start'})
        self.await_state(lambda s:s['runtime']['status']=='running')

    def tearDown(self):
        self.request('/api/control', {'desired':'stop'})
        self.await_state(lambda s:s['runtime']['status']=='stopped')

    @staticmethod
    def device(s,name): return next(d for d in s['devices'] if d['name']==name)

    def test_drive_through_pedro_and_encoders_then_neutral(self):
        before=self.request('/api/state')['pose']['x']
        self.request('/api/input', {'left_stick_y':-.6})
        s=self.await_state(lambda s: all(abs(self.device(s,n)['power'])>.5 for n in ('lf','lr','rf','rr')))
        self.assertLess(self.device(s,'lf')['power'],0)  # The actual BioBuzz left-motor reversal.
        self.await_state(lambda s: abs(self.device(s,'rf')['encoder'])>30 and s['pose']['x']>before+1)
        self.request('/api/input', {'left_stick_y':0})
        self.await_state(lambda s:all(abs(self.device(s,n)['power'])<.001 for n in ('lf','lr','rf','rr')))

    def test_intake_press_release_and_lift_bumpers(self):
        self.request('/api/input', {'a':True})
        self.await_state(lambda s:self.device(s,'intakeMotorFront')['power']>.99 and self.device(s,'intakeMotorBack')['power']>.99)
        self.request('/api/input', {'a':False})
        self.await_state(lambda s: self.device(s,'intakeMotorFront')['power']==0 and self.device(s,'intakeMotorBack')['power']==0)
        self.request('/api/input', {'right_bumper':True})
        self.await_state(lambda s:self.device(s,'intakeServoFront')['position']<.01)
        self.request('/api/input', {'right_bumper':False,'left_bumper':True})
        self.await_state(lambda s:self.device(s,'intakeServoFront')['position']>.99)
        self.request('/api/input', {'left_bumper':False})

    def test_transfer_trigger_starts_and_stops(self):
        self.request('/api/input', {'right_trigger':1})
        self.await_state(lambda s:self.device(s,'transferMotor')['power']>.99)
        self.request('/api/input', {'right_trigger':0})
        self.await_state(lambda s:self.device(s,'transferMotor')['power']==0)

    def test_diagnostics_shooter_turret_and_emergency_stop(self):
        self.request('/api/action', {'name':'shooter','rpm':2500})
        self.await_state(lambda s:self.device(s,'shooterMotor')['velocity']>1000)
        self.request('/api/action', {'name':'turret','position':.8})
        self.await_state(lambda s:abs(self.device(s,'turretServoBack')['position']-.8)<.01)
        self.request('/api/control', {'desired':'stop'})
        self.await_state(lambda s: all(not d['enabled'] for d in s['devices']))

    def test_missing_browser_heartbeat_stops_motor_outputs(self):
        self.request('/api/input', {'a':True})
        self.await_state(lambda s:self.device(s,'intakeMotorFront')['power']>.99)
        self.await_state(lambda s:s['runtime']['status']=='stopped' and all(d.get('power',0)==0 for d in s['devices']),timeout=5)


if __name__=='__main__': unittest.main()
