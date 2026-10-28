# BioBuzz desktop robot lab

The source snapshot is BioBuzz **797d3603999e7a039510278b049f039deab43ba3**, fetched
from `https://github.com/simplyrohan/BioBuzz`. `TeamCode/` is a standalone copy;
builds do not read or write the original BioBuzz checkout. `UPSTREAM.txt` records
the revision, and `upstream-source.sha256.json` records the untouched source hashes.
The original checkout was reset and pulled at the user's explicit request before
copying. All subsequent adaptations are in this ftcsim repository.

## Run

From the ftcsim repository root, with JDK 17+ and Python 3.9+ installed:

```sh
./run-biobuzz.sh
```

Open **http://127.0.0.1:8085**. This command builds the Java/Kotlin runtime, starts
the Python Lynx endpoint on **9015**, serves the dashboard, and launches the actual
copied `org.firstinspires.ftc.teamcode.opmodes.Tele` on the JVM. It uses the real
Pedro Pathing 3.0.2 and SolversLib 0.3.6 dependencies; it does not reimplement the
TeleOp's drivetrain mixing or gamepad bindings in Python.

Click **INIT**, then **START**. Use the controls on the page or:

| Input | Action in copied TeleOp |
|---|---|
| W / S | Forward / reverse |
| A / D | Strafe |
| Q / E | Turn |
| Hold Space (gamepad A) | Run both intake motors |
| Release Space | Stop both intake motors |
| R (right bumper) | Lower intake servos |
| F (left bumper) | Raise intake servos |
| Hold T (right trigger) | Run transfer motor |
| Release T | Stop transfer motor |
| Escape / STOP | Stop the OpMode and disable simulated outputs |

A browser-compatible controller is also supported: left stick drives, right
stick turns, A operates intake, bumpers operate lift, and right trigger operates
transfer. Click the page outside text/number inputs before using keyboard keys.
On narrow screens, controls appear below the motor/servo displays.

The diagnostics panel can command shooter RPM and normalized turret servo
positions while running. These explicit diagnostic actions execute on the same
JVM runner thread and go through real SDK controllers and the Lynx TCP bridge;
they are distinct from the TeleOp's existing controller bindings.

The dashboard shows all 8 motors and 4 servos, activity, signed applied power,
encoder ticks and velocity, servo PWM, a simple moving robot pose, and recent
Lynx writes/errors. The complete wire log is `simulator/build/biobuzz-wire.jsonl`.
User controls never write motor state directly: the copied Kotlin OpMode (or an
explicit diagnostic action) must issue SDK calls to produce output.

Ctrl-C in the simulator terminal shuts down the child JVM and servers. STOP
sends failsafe commands in addition to the user's `stop()` method. If the browser
input heartbeat or JVM runtime disappears for 2 seconds, simulated motor outputs
are disabled. INIT creates a fresh OpMode and invalidates SDK controller caches
so repeat start/stop cycles work after failsafe.

Override ports if required:

```sh
./run-biobuzz.sh --port 8086 --lynx-port 9016
```

Use `--no-build` only after a successful build when sources have not changed.

## Copy-only changes

These adaptations do not change the original BioBuzz checkout:

1. **Constants.java:** substitute `SimLocalizer` for the physical Pinpoint
   localizer. It feeds the actual Pedro follower with the Python model's pose and
   velocity. A USB/I2C Pinpoint driver is not emulated.
2. **Transfer.kt:** correct the duplicated `if (value)` stop branch to
   `if (!value)`. Upstream otherwise immediately writes power 0 after power 1,
   and never stops on release.
3. **Shooter.kt:** replace robot-specific Marrow Settings reads with explicit
   simulation defaults (`linear`, coefficients `[0.0, 0.0]`). No shooter LUT was
   provided. Convert RPM to SDK ticks/second using `/ 60.0`; the original formula
   omits that conversion. Real robot coefficients/calibration are not invented.
4. **Tele.kt:** remove the unused Panels Gamepad import. The existing TeleOp
   controls, Pedro follower, and SolversLib commands are retained.

The copied upstream `robot.reset()` call after `Robot` construction is retained.
In SolversLib, this discards subsystem registrations, so the current TeleOp does
not automatically execute shooter/turret `periodic()` methods. The diagnostics
let you exercise those outputs explicitly. This is a source behavior to review
before expecting auto-aim; the simulator does not claim to validate auto-aim.
Turret degree-to-servo calibration is also still an upstream placeholder.

Other OpModes (Auto, ShooterTuning) and Pedro tuning procedures are preserved in
the copy but excluded from this initial desktop build. The validated target is
**Red TeleOp**, not the Android Panels/tuning interfaces or LinearOpMode.

## Hardware/model assumptions

`robot.json` maps the names requested by BioBuzz to simulated channels:

- Hub 1 motors 0–3: `lf`, `lr`, `rf`, `rr`.
- Hub 2 motors 0–3: intake front, intake back, shooter, transfer.
- Hub 2 servos 0–3: intake front lift, intake back lift, turret back, turret front.

No hardware configuration XML was supplied, so these port assignments are
simulation assumptions. `robot.json` is the single source of names and channels.
The motion model currently assumes this listed hub/port drive layout.

The model integrates idealized motor velocities at up to 2800 ticks/second,
produces encoder/bulk responses, and estimates mecanum motion at up to 48 inches
per second. It respects enable state and basic motor modes. It has no measured
mass/inertia, collision/contact physics, game pieces, accurate battery/current
model, or hardware-calibrated motor constants. Servo visualization assumes the
SDK's 600–2400 µs range. This is useful for control-flow, command, binding, and
subsystem activation debugging, not validating PID gains or match trajectories.

## Checks

```sh
./gradlew :simulator:build :simulator:installDist
```

This compiles the extracted SDK, real Pedro/SolversLib dependencies, and the
copied BioBuzz Kotlin sources. The Python integration checks launch a separate
JVM and verify drive power/signs and encoders, intake press/release, intake lift,
transfer trigger, shooter/turret diagnostics, repeat lifecycle cycles, STOP,
and loss-of-browser heartbeat, alongside the existing Lynx protocol tests.
