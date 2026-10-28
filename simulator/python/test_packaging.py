"""Verify that package boundaries and the relocated release launcher are usable."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_sdk_is_an_independent_library(self):
        sdk = ROOT.parent/'sdk/jvm/build/libs/ftc-sdk-jvm-12.0.0.jar'
        with zipfile.ZipFile(sdk) as archive:
            names = set(archive.namelist())
        self.assertIn('com/qualcomm/hardware/lynx/LynxModule.class', names)
        self.assertIn('com/qualcomm/robotcore/hardware/DcMotorImplEx.class', names)
        self.assertIn('android/content/Context.class', names)
        self.assertIn('ftcsim/jvm/DesktopRuntime.class', names)
        self.assertIn('META-INF/FTC-SDK-LICENSE', names)
        self.assertNotIn('ftcsim/jvm/BioBuzzRunner.class', names)
        self.assertNotIn('ftcsim/jvm/TcpLynxTransport.class', names)
        self.assertFalse(any(name.startswith('org/firstinspires/ftc/teamcode/') for name in names))

    def test_driver_does_not_duplicate_the_sdk(self):
        with zipfile.ZipFile(ROOT/'build/libs/ftcsim-driver-0.1.0.jar') as archive:
            names = set(archive.namelist())
        self.assertIn('ftcsim/jvm/BioBuzzRunner.class', names)
        self.assertIn('META-INF/BIOBUZZ-LICENSE', names)
        self.assertIn('ftcsim/jvm/TcpLynxTransport.class', names)
        self.assertIn('org/firstinspires/ftc/teamcode/opmodes/Tele.class', names)
        self.assertNotIn('com/qualcomm/hardware/lynx/LynxModule.class', names)
        self.assertNotIn('android/content/Context.class', names)

    def test_relocated_simulator_without_gradle_or_checkout(self):
        with tempfile.TemporaryDirectory(prefix='ftcsim-package-') as temporary:
            package = Path(temporary)/'robot lab'  # Exercise paths containing spaces, too.
            shutil.copytree(ROOT/'build/install/ftcsim', package)
            self.assertFalse((package/'gradlew').exists())
            self.assertFalse((package/'build/classpath.txt').exists())
            self.assertTrue((package/'lib/ftc-sdk-jvm-12.0.0.jar').exists())
            log_path = Path(temporary)/'runner.log'
            with log_path.open('w') as log:
                process = subprocess.Popen([str(package/'bin/biobuzz'), '--port', '0', '--lynx-port', '0'],
                                           cwd=temporary, stdout=log, stderr=log, start_new_session=True)
                try:
                    deadline = time.monotonic()+15
                    base = None
                    while time.monotonic()<deadline:
                        lines = log_path.read_text().splitlines()
                        base = next((line.split(': ',1)[1] for line in lines if line.startswith('BioBuzz simulator: ')), None)
                        if base: break
                        if process.poll() is not None: self.fail(log_path.read_text())
                        time.sleep(.05)
                    self.assertIsNotNone(base, log_path.read_text())
                    def call(path, data=None):
                        target = base+path if data is None else Request(base+path,json.dumps(data).encode(),{'Content-Type':'application/json'})
                        with urlopen(target,timeout=3) as response: return json.load(response)
                    def await_state(predicate):
                        deadline = time.monotonic()+8
                        while time.monotonic()<deadline:
                            state=call('/api/state')
                            if state['runtime']['status']=='error': self.fail(state['runtime']['error']+'\n'+log_path.read_text())
                            if predicate(state): return state
                            time.sleep(.05)
                        self.fail(log_path.read_text())
                    await_state(lambda s:s['runtime']['status']=='idle')
                    call('/api/control',{'desired':'init'})
                    await_state(lambda s:s['runtime']['status']=='initialized')
                    call('/api/control',{'desired':'start'})
                    await_state(lambda s:s['runtime']['status']=='running')
                    call('/api/input',{'a':True})
                    await_state(lambda s:any(d['name']=='intakeMotorFront' and d['power']>.99 for d in s['devices']))
                    call('/api/input',{'a':False})
                    await_state(lambda s:any(d['name']=='intakeMotorFront' and d['power']==0 for d in s['devices']))
                    call('/api/control',{'desired':'stop'})
                    await_state(lambda s:s['runtime']['status']=='stopped' and all(not d['enabled'] for d in s['devices']))
                finally:
                    if process.poll() is None:
                        process.send_signal(signal.SIGINT)
                        try: process.wait(timeout=8)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid,signal.SIGKILL)
                            process.wait()
