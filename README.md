# ftcsim

FTC SDK 12.0.0 on a desktop JVM, with a Python device simulator and browser Driver
Station. Install the Python package once, then configure any FTC robot project.

## Install and run

```sh
pipx install ftcsim
cd /path/to/your/FTC-project
ftcsim --wizard
ftcsim
```

`ftcsim` starts the simulator on IPv4 loopback port 9015. Open
[the Driver Station](http://localhost:9015/ds). In another terminal in your robot
project, run `./gradlew runSimulator` (JDK 17+ required), select an OpMode,
then open **Hardware map**, add your devices, and **Apply to SDK** before INIT
and START. The robot project compiles its TeamCode against the precompiled
SDK shipped in the Python package. End users do not need this source checkout or
a build of the FTC SDK. `python -m ftcsim` is equivalent to the installed CLI.

```sh
ftcsim --port 9016                  # use a different simulator port
ftcsim -w --project /path/to/robot  # configure another project
ftcsim -w --dry-run               # preview setup
ftcsim -w --yes                   # noninteractive setup
ftcsim -w --copy-sdk              # copy JARs rather than link this installation
ftcsim --help
```

Hardware maps belong to the Driver Station browser. The dedicated
`/ds/hardware` page provides driver selection, names, hub/port assignments,
device settings, and nested Pinpoint pod configuration. **Load from file** and
**Save to file** import/export portable JSON maps. Drag-and-drop and
**Paste JSON instead** also load maps when file dialogs are unavailable. Edits persist in
localStorage per simulator origin and SDK address. Saved maps restore when the
DS reconnects; a new SDK starts empty and waits for the DS to apply a map.
Loaded maps display device counts and named driver cards immediately. If browser
storage is blocked, the map remains usable in the current tab and can be saved to
a file. Apply succeeds only after the SDK confirms the map and the simulator
reports the matching physical devices, including nested encoders.
The setup wizard does not request, import, or generate hardware configuration.

For a custom port, launch the robot with
`./gradlew runSimulator -PsimEndpoint=ws://localhost:9016/sim`.
The wizard preserves robot sources, adds a `TeamCodeSim` Gradle module, discovers
annotated OpModes, and creates IDE run configurations. It backs up changes under
`.ftcsim/backups`, preserves user configuration, and refuses to overwrite edited
managed files unless `--force` is supplied. Supply `--kotlin-version` if a Kotlin
project does not declare a root Kotlin plugin. Re-run the wizard after moving or
upgrading your Python installation. `--sdk` can override the compiled bundle path.

The generated backend task remembers the Python executable used for setup;
`-PsimPython=/path/to/python` overrides it. Running `ftcsim` directly is also supported.
Pipx exposes the CLI on PATH; ordinary pip installs expose it in that Python
environment's scripts directory.

## Build distributions

```sh
python3 -m pip install build
python3 -m build
pipx install dist/ftcsim-0.1.0-py3-none-any.whl
```

Wheel builds automatically run `scripts/build_sdk.py`, which invokes the separate
`sdk/desktop` Gradle build and packages the modified SDK, desktop runtime, and all
JVM dependency JARs. JDK 17+ is required when building; first builds need network
access for Gradle dependencies. No Java compiler runs when installing a wheel.
The source distribution includes modified FTC SDK sources and build tooling, so
building a wheel from the source distribution follows the same compilation path.
SDK source files are excluded from the wheel. The bundled SDK license and a JAR
SHA-256 manifest are included. This is a large wheel because it includes Android
API compatibility definitions and upstream JVM dependencies.

For development:

```sh
python3 -m pip install -e .
cd sdk/desktop
./gradlew build :runtime:writeClasspath
cd ../..
```

`python3 scripts/build_sdk.py` explicitly refreshes the packaged binaries.
See [the driver guide](DRIVERS.md) for device configuration, modeling, and extension.

## Architecture and limits

- `src/ftcsim/`: CLI, setup wizard, Gradle templates, HTTP/WebSocket server,
  modular device drivers, hub register routing, and browser Driver Station.
- `sdk/`: editable upstream FTC sources, desktop platform shims, reusable Java
  runtime. Its Android build remains independent.
- `scripts/build_sdk.py`: compiles and stages the wheel's JVM binaries.
- [PROTOCOL.md](PROTOCOL.md): WebSocket messages and connection ownership.

The browser controls Java directly on port 1115. Java connects to Python once on
`/sim`; Python serves the page and streams physical device state over `/sim/drivers`. Actual SDK controllers,
Lynx payload serializers/decoders, telemetry, gamepads, and iterative/linear
lifecycle execute on Java. Disconnects disable modeled outputs; simulator
transport loss requires restarting the SDK.

Built-in drivers cover DC motors, servos, passive odometry pods, and goBILDA
Pinpoint with two nested encoder inputs. Pinpoint supports the SDK's real I²C
register reads/writes, configurable bulk reads, CRC, position, velocity, and yaw.
Full motor power defaults to 2800 ticks/second with instantaneous acceleration.
Servo position follows enabled PWM commands without load or travel-time modeling.

Sensors consume explicit body motion in mm/s and rad/s, supplied through the
simulator's sensor-motion panel or `Robot.set_motion()`. There is no chassis model
yet, so motor power does not generate robot motion. The planar IMU is ideal, with
zero pitch/roll and no noise. Cameras, other I²C sensors, Android services, and
physical FTC Driver Station connections remain unsupported.
