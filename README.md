# FTC desktop simulator

FTC SDK 12.0.0 on a desktop JVM, connected to an independent Python motor simulator
and a browser Driver Station. All Java, robot programs, and build tooling live in
`sdk/`. Python and the static browser page live in `sim/`.

```text
Browser Driver Station                 Desktop FTC SDK
http://localhost:9015/ds  ── WS ──────► localhost:1115/ds
                                          │
                                 OpMode → SDK controllers
                                          │
                                          ▼ one persistent WS
Python motor model ◄──────────────── localhost:9015/sim
```

The SDK opens its simulator connection and starts the DS listener during bootstrap,
before constructing an OpMode. Python does not start Java or hold Driver Station
state. The DS page talks directly to the SDK. Its only simulator read is the
physical motor display.

## Run

Start Python in one terminal (Python 3.10+):

```sh
cd sim
python3 -m pip install -r requirements.txt
python3 server.py
```

Start the copied BioBuzz robot in another terminal (JDK 17+):

```sh
cd sdk/desktop
./gradlew :biobuzz:run
```

Open [the Driver Station](http://localhost:9015/ds), select **Red TeleOp**, then
**INIT** and **START**. Space/gamepad A runs the intake; WASD drives; Q/E are
bumpers; R/F are triggers. Both browser gamepads and on-screen inputs are supported.
STOP calls the SDK lifecycle stop and disables hub outputs.

For an SDK-only motor example, run `./gradlew :runtime:run` instead. Its default
configuration is one motor named `motor` on hub 1, port 0. Select **Motor demo**
or **Linear motor demo**. A drives the motor and encoder feedback appears as
real OpMode telemetry. Configuration can be edited and applied from the DS while
stopped. BioBuzz's configuration is a copied assumption, not an imported robot XML.

## Layout and limits

- [`sdk/`](sdk/README.md): editable upstream modules, desktop compatibility adapters,
  reusable runtime, and isolated robot examples. Its `desktop/` build creates JARs;
  its independent Android workspace remains at `sdk/`.
- [`sim/`](sim/README.md): Python HTTP/WS server, independent hub/motor model,
  static `ds/` page, and integration tests. No Java sources or binaries.
- [`PROTOCOL.md`](PROTOCOL.md): message formats and connection ownership.

The model tracks motor enable, mode, power/speed, and encoders. It retains basic
servo register handling for BioBuzz, but has no field physics, pose or Pedro
localization service. The BioBuzz copy uses an example-only stationary localizer.
Camera, I2C sensor models, Android UI/services, and a physical FTC DS connection
are not implemented. JSON DS messages replace Robocol packets; real SDK gamepads,
controllers, telemetry composition, and iterative/linear lifecycle execution remain.

## Validation

```sh
cd sdk/desktop
./gradlew build :runtime:writeClasspath :biobuzz:writeClasspath
cd ../../sim
python3 -m unittest discover -s tests -v
```

Integration tests launch the built SDK and exercise both WebSockets, lifecycle,
configuration, two gamepads, actual Lynx payloads/response decoders, telemetry,
BioBuzz motor activation/release, and disconnect handling. These tests do not
validate complete physical hardware behavior.

The previous implementation is preserved on Git branch `archive/native-tcp` at
`0a35cc6`. The original BioBuzz checkout is not a build input and remains untouched.
