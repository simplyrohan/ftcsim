# Custom protocols and file formats

WebSocket messages are UTF-8 JSON text. Numeric Lynx payloads retain the SDK's
little-endian binary layout and are represented as hexadecimal strings.

## SDK ⇄ simulator: `/sim`

Requests include `version: 1` and an integer `id`. Replies echo the ID. One SDK
owns the simulator at a time; losing this transport disables outputs and requires
restarting that SDK process.

```json
{"version":1,"type":"configure","id":1,"devices":[{"name":"drive","type":"motor","module":1,"port":0}],"validateOnly":false}
```

`configure` validates the complete device tree before replacing hardware.
`validateOnly: true` performs the same validation without changing state.
Invalid configuration preserves the previous hardware. Successful configuration
returns `{"type":"configure","id":1,"status":"ack","payload":""}`.

```json
{"version":1,"type":"lynx","id":2,"module":1,"command":"com.qualcomm.hardware.lynx.commands.core.LynxSetMotorConstantPowerCommand","payload":"00ff7f","response":null}
```

`command` names the SDK command class. `payload` contains its serialized payload,
not a full USB datagram. `response` is the expected response class or `null`.

| Reply status | Fields |
| --- | --- |
| `ack` | `type`, `id`, empty `payload` for writes. |
| `response` | `type`, `id`, hexadecimal `payload` for reads. |
| `nack` | `type`, `id`, `reason: 255` for unsupported commands. |
| `error` | `type`, `id` when available, explanatory `message`. |

Messages are limited to 1 MiB. SDK requests time out after three seconds.

## Driver Station ⇄ SDK: `/ds`

This is a custom JSON protocol, independent of FTC Robocol framing. The first
client receives control; later clients observe. A new connection can claim
control after the controller disconnects.

The SDK initially sends:

```json
{"type":"role","controller":true}
```

```json
{"type":"hello","version":1,"opmodes":[{"name":"Example","class":"team.Example","flavor":"teleop"}],"devices":[],"hardwareConfigured":false}
```

```json
{"type":"status","state":"idle","selected":"Example","elapsed":0,"error":"","simulatorConnected":true}
```

The latest telemetry follows if available. OpModes are supplied by the consuming
robot project. An SDK with no supplied OpModes advertises an empty list.

### Requests

Only the controller may send requests. Except for `heartbeat`, requests receive
an `ack` or `error` with a `message`; an optional request `id` is echoed.

| Type | Fields and semantics |
| --- | --- |
| `select` | `name`: advertised OpMode name; inactive only. |
| `configure` | `devices`: complete hardware tree; inactive only. |
| `init` | Initializes the selected OpMode; requires configured hardware. |
| `start` | Starts an initialized OpMode. |
| `stop` | Stops the OpMode, disables outputs, and invalidates controller caches. |
| `gamepads` | `gamepad1`, `gamepad2`: input objects; omitted fields are neutral. |
| `heartbeat` | Refreshes controller liveness; no reply. |

Gamepad axes `left_stick_x`, `left_stick_y`, `right_stick_x`, and `right_stick_y`
range from -1 to 1. `left_trigger` and `right_trigger` range from 0 to 1.
Buttons are booleans: `a`, `b`, `x`, `y`, `dpad_up`, `dpad_down`, `dpad_left`,
`dpad_right`, `left_bumper`, `right_bumper`, `left_stick_button`,
`right_stick_button`, `guide`, `start`, `back`, and `touchpad`.

The SDK neutralizes gamepads after 500 ms without an input update and stops the
OpMode after 1.5 seconds without controller messages, or on controller disconnect.
Heartbeats keep the session alive without preserving stale gamepad input.
An unresponsive OpMode makes the SDK reject another INIT until restarted.
Requests are limited to 65,536 Java string characters; the command queue holds
256 entries.

### Events

| Type | Fields |
| --- | --- |
| `status` | `state`: `idle`, `initialized`, `running`, `stopped`, or `error`; `selected`, `elapsed` in seconds, `error`, `simulatorConnected`. |
| `hello` | Updated `opmodes`, `devices`, and `hardwareConfigured` after configuration. |
| `telemetry` | `tag` and `data`: caption → string/number values from SDK telemetry. |
| `command` | SDK command `name` and `extra`, including telemetry display format. |
| `robocol` | `kind` and base64 `payload` for other serialized SDK data. |
| `ack` / `error` | `message` and optional echoed `id`. |

The hardware map lasts for the SDK process lifetime. Explicitly configuring an
empty map sets `hardwareConfigured: true`. Mechanisms and visual model metadata
are never sent to the SDK.

## Driver Station ⇄ simulator

Browser writes must have the simulator's origin. Requests without an Origin
header are accepted for local program clients.

### `/sim/drivers` WebSocket

The server sends `{"type":"drivers","drivers":[...]}` once, then a physical
snapshot approximately every 100 ms. `GET /sim/state` returns the same snapshot.

```json
{"type":"state","connected":true,"commands":0,"devices":[],"mechanisms":[],"mechanism_configuration":[],"mechanism_error":"","motion":{"vx":0,"vy":0,"angular_velocity":0}}
```

`connected` describes the SDK transport; `commands` counts accepted Lynx commands.
Device snapshots contain `name`, `type`, `connection`, `port`, `state`, and
recursive `children`; root devices also contain `module`. Mechanism snapshots
contain `name`, `type`, `drivers`, and `state`. `mechanism_configuration` contains
applied physics definitions; `mechanism_error` reports suspended bindings.

Supported inputs:

```json
{"type":"ping","id":1}
```

The reply is `{"type":"pong","id":1}`. IDs must be integers. This probe does
not change simulation state.

```json
{"type":"motion","vx":100,"vy":0,"angular_velocity":0.2}
```

Motion is robot-relative: forward/left mm/s and counterclockwise rad/s. Omitted
components are zero; values must be finite and bounded to ±10,000 mm/s and
±100 rad/s. A connected SDK is required. Replies are `ack` or `error` with a
`message`. Motion persists until replaced or a failsafe, STOP, disconnect, or
hardware reconfiguration clears it. Mechanism-bound sensors use mechanism motion
instead. Input messages on this socket are limited to 64 KiB.

### HTTP endpoints

| Endpoint | Contract |
| --- | --- |
| `GET /sim/driver-types` | Driver catalog: `type`, `label`, `connection`, `ports`, `child_ports`, `child_connections`, `child_defaults`, `options`, `presets`. |
| `GET /sim/mechanism-types` | Mechanism catalog: `type`, `label`, `description`, `drivers`, `options`, `exclusive`. Driver slots specify `name`, `label`, accepted `types`, `required`, and optional child requirements. |
| `POST /sim/mechanisms` | `{"mechanisms":[...]}`; atomically replaces physics definitions and returns a snapshot. Invalid requests return HTTP 400 with `message`. Success includes `Server-Timing: mechanisms;dur=<milliseconds>`. |
| `POST /sim/mechanisms/place` | `{"mechanism":"drivebase","x_mm":0,"y_mm":0,"heading_deg":90}`; places an applied drivetrain with stopped motors and returns a snapshot. Invalid requests return HTTP 400 with `message`. |

Option metadata contains `name`, `label`, `type`, and `default`, with optional
`min`, `max`, and `choices`. Choices are scalar values or `{value,label}` objects.
HTTP request bodies are limited to 1 MiB.

Replacing mechanisms resets drivetrain pose while preserving driver state.
Field placement changes physical pose without changing encoder counts or IMU
coordinates. Hardware replacement rebinds retained mechanisms; incompatible
bindings suspend the mechanism set and populate `mechanism_error`.

## Hardware definitions

```json
{"name":"drive","type":"motor","module":1,"port":0,"options":{"max_rpm":312,"ticks_per_revolution":537.7,"direction":1}}
```

Device fields are `name`, `type`, `module`, `port`, optional `options`, and optional
`children`. Root hub addresses are integers 1–254. Motor/encoder/I²C ports are
0–3; servo ports are 0–5. A motor occupies both its motor and encoder port.
Names are unique across the tree and cannot use the reserved `hubN` pattern.

Pinpoint children are odometry devices on string ports `x` and `y`, with no
`module`. Their `axis` defaults to the parent port. Child devices are part of the
parent and do not create separate SDK HardwareMap entries.

Driver options are advertised by the catalog. Motor speed is output-shaft RPM;
encoder resolution is ticks per output-shaft revolution. Physical `direction`
is 1 or -1 and is independent of SDK motor direction. Pod `offset_mm`,
`ticks_per_mm`, and `direction` describe physical mounting and wiring. Pinpoint
resolution and offsets configure its estimator independently of physical pods.
Legacy `max_ticks_per_second` motor values are converted to RPM when read.

`servo` creates an SDK `ServoImplEx`; `cr_servo` creates `CRServoImplEx` and
uses the same servo-port/PWM protocol. They cannot share one physical port.
CR servo options add `max_rpm` (default 60) and physical `direction` (1 or -1).
Its default pulse range is 600–2400 µs, matching the SDK's standard range.
Power is linear from -1 to 1 around the pulse-range midpoint. Snapshots report
`position` in accumulated shaft revolutions, `velocity` in revolutions/second,
and `shaft_rpm`; no encoder is exposed to TeamCode. Disabling PWM or a failsafe
stops rotation and preserves shaft position.

## Mechanism definitions

```json
{"name":"drivebase","type":"mecanum","drivers":{"front_left":"lf","front_right":"rf","rear_left":"lr","rear_right":"rr","pinpoint":"pinpoint"},"options":{"wheel_diameter_mm":96,"gear_ratio":1,"wheelbase_mm":360,"track_width_mm":360,"lateral_multiplier":1,"front_left_direction":1,"front_right_direction":1,"rear_left_direction":1,"rear_right_direction":1}}
```

Fields sent to Python are `name`, `type`, `drivers`, and optional `options`.
Names must be unique; a definition's driver references must exist and satisfy
the catalog's slot requirements. Exclusive mechanisms cannot share consumed
drivers, including nested sensor inputs. Configuration is limited to 64 mechanisms.

Mecanum dimensions are millimeters; `gear_ratio` is motor output turns per wheel
turn. Mounting directions multiply physical motor directions. Optional `pinpoint`
binds its existing X/Y pods. Pose uses `x_mm`, `y_mm`, and `heading_rad`; velocity
uses forward/left mm/s and counterclockwise rad/s.

`tank` uses the same dimensions, gearing, pose, sensor binding, and placement
contract. Required driver slots are `left` and `right`; `rear_left` and
`rear_right` are optional additional motors. Each side's speed is its motors'
average; forward speed is `(left + right) / 2`, lateral speed is zero, and yaw
rate is `(right - left) / track_width_mm`. `wheelbase_mm` sets visual length.
Each motor slot has a corresponding `<slot>_direction` option (1 or -1).

```json
{"name":"drivebase","type":"tank","drivers":{"left":"left_drive","right":"right_drive"},"options":{"wheel_diameter_mm":96,"track_width_mm":402}}
```

Custom mechanisms optionally bind one motor or servo through `drivers.actuator`.
They observe inputs without changing drivers or driving sensors. Their options
are `motion` (`rotation` or `translation`), `axis` (`x`, `y`, or `z`), `direction`
(1 or -1), `travel`, and `input_zero`:

```text
displacement = (input - input_zero) * travel * direction
```

Motor and CR servo input is signed physical shaft revolutions; positional servo
input is normalized 0–1.
`travel` is degrees for rotation or millimeters for translation per input unit.

## Robot archive: `.fs`

An `.fs` file is a ZIP archive:

```text
robot.json
models/model-1.glb
models/model-2.glb
```

`robot.json` has this shape:

```json
{"format":"ftcsim.robot-configuration","version":2,"notes":"Optional text","devices":[],"mechanisms":[],"assets":{"model-id":"models/model-1.glb"}}
```

`devices` contains hardware definitions. `mechanisms` contains the physics
fields above plus optional browser-only `visual` metadata:

```json
{"model":{"id":"model-id","name":"turret.glb"},"position":[0,0,100],"rotation":[0,0,90],"scale":1,"parent":"drivebase"}
```

Positions use millimeters with X forward, Y left, Z up. Rotations are roll X,
pitch Y, yaw Z in degrees, composed yaw → pitch → roll. `scale` is a positive
GLB geometry multiplier. An empty or omitted `parent` means world origin;
otherwise placement follows that mechanism's moving origin. Parent references
must exist and cannot form cycles. Geometry scale does not scale child offsets
or actuator travel. Model origins are preserved.

`assets` maps opaque model IDs to `models/<filename>.glb`; each referenced ID
must exist. Shared IDs reuse one file. Model upload names are metadata, not paths.
Imports assign fresh IDs to avoid overwriting existing browser assets.

Archive and validation limits:

- 512 MiB compressed and expanded, at most 130 ZIP entries.
- `robot.json`: 1 MiB; each GLB: 200 MiB; at most 64 asset-map entries.
- Stored and deflate ZIP compression are supported.
- Duplicate paths, absolute paths, backslashes, NULs, and empty/`.`/`..` segments
  are rejected. Unused safe entries are ignored but count toward limits.
- Models must be self-contained binary glTF 2.0. Embedded buffers/textures and
  Draco and Meshopt geometry compression are supported; required KTX2 extensions
  are rejected. Draco decoding uses bundled local assets.
- Hardware trees contain at most 256 root devices, 1,024 devices total, and eight
  child nesting levels.

Invalid archives preserve the existing configuration. Standalone version 1 JSON
robot files remain readable: they use the same root format and definitions but
map model IDs to base64 GLBs in `assets`. Exports use version 2 ZIP archives.
SDK addresses, live state, and per-OpMode start presets are excluded.
