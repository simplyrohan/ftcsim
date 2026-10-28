# Physical device drivers

Drivers are built into ftcsim, with Python models in `src/ftcsim/drivers/` and
Svelte counterparts in `driver-station/src/lib/model/widgets.ts`. There is no end-user plugin
installation mechanism.

## Device model

`Driver` defines `advance(dt, motion)`, `step`, `failsafe`, `state`, `snapshot`,
and child attachment. The base lifecycle advances children before their parent,
so a Pinpoint reads the current tick's pod data. A device has one physical owner;
children are never registered or advanced again as hub devices.

`Encoder` adds fractional tick position, tick velocity, reset, and signed 32-bit
counter wrapping. Both `DCMotor` and `OdometryPod` inherit it. A motor integrates
power or target velocity, honors enable and run-to-position commands, and stops
at its configured tolerance without overshooting. An odometry pod is passive: its
counts come from body motion, mounting offset, resolution, and wiring direction.

`Servo` retains its physical normalized position when PWM is disabled. While
PWM is enabled, position follows the commanded pulse width instantly.

`I2CDriver` defines register reads/writes and address selection. `GoBildaPinpoint`
extends it with two encoder child connections (`x` forward and `y` left), planar
IMU yaw, offset compensation, SE(2) pose integration, and the SDK 12 firmware-v3
register protocol, including configurable bulk reads and CRC-8.
Missing pods produce the corresponding SDK fault status. Reset and 250 ms IMU
calibration status are modeled. Pitch and roll are zero; there is no IMU drift,
noise, slip, collision, or torque. Mecanum chassis motion is supplied by the
optional [mechanism layer](MECHANISMS.md).

`physics/model.py` owns hubs and routes Lynx traffic to driver instances.
`I2CBus` translates Lynx transactions and status queries to a device's register
interface. Register serialization uses the real SDK's little-endian payloads.
The Java runtime registers SDK counterparts in `DesktopDeviceDrivers.java`:
motor and hub pod use `DcMotorEx`, servo uses `ServoImplEx`, and Pinpoint uses the
original `GoBildaPinpointDriver` with `LynxI2cDeviceSynchV2`.

## Configuration

Use the Driver Station's **Settings → Hardware map** modal to add drivers,
set names and hub/port assignments, edit device settings, and attach/remove
Pinpoint's X/Y pods. The editor is generated from the Python driver catalog's
configuration metadata. Adding a driver does not require adding form fields to
the browser by hand. `/ds/hardware` also opens this settings section.

Edits save automatically in localStorage, scoped to the simulator origin and
SDK WebSocket address. **Apply to SDK** sends the full map through the SDK's DS
connection while stopped. The SDK creates real hardware objects and synchronizes
the physical model. Saved maps restore automatically when the DS reconnects to
an idle SDK. INIT is disabled until the saved map is applied. Page navigation
keeps the same controller connection open.

The SDK starts with an empty map. The setup wizard no longer imports XML or
creates robot.json, and the generated Gradle target does not pass a config file.
Browser storage is the authority; the SDK's advertised map never overwrites the
local draft. Clearing browser storage removes the saved map. Another origin,
port, browser profile, or SDK address uses separate storage. Changes from another
tab are surfaced and require applying while stopped.

**Load from file** uses a visible native file control. You can also drop a JSON
file onto the drop area or expand **Paste JSON instead**, paste the file contents,
and select **Load JSON** when an embedded browser blocks file dialogs. Every
input path imports a portable JSON map, validates the entire topology and
all driver options, then saves it as the browser's draft. It does not change the
SDK until **Apply to SDK** is pressed. Invalid files preserve the previous draft
and applied map. If browser storage is unavailable, a valid loaded map remains
usable in the current tab and can be saved to a file. Files are limited to 1 MiB.

**Save to file** downloads the current valid draft as `ftcsim-hardware-map.json`.
Files contain `format: "ftcsim.hardware-map"`, `version: 1`, `devices`, and optional
text `notes`. Nested pod configurations are included. SDK addresses, browser
storage keys, and live device state are excluded, so files can move between
browsers and SDK instances. Notes are displayed after loading and retained on
export. File operations work without an SDK connection.

The editor sends device definitions in this shape:

```json
{
  "devices": [
    {"name": "drive", "type": "motor", "module": 1, "port": 0},
    {"name": "arm", "type": "servo", "module": 1, "port": 0},
    {"name": "hubPod", "type": "odometry", "module": 1, "port": 1,
     "options": {"axis": "x", "ticks_per_mm": 13.26291192}},
    {"name": "pinpoint", "type": "pinpoint", "module": 1, "port": 0,
     "children": [
       {"name": "forwardPod", "type": "odometry", "port": "x",
        "options": {"offset_mm": -100}},
       {"name": "strafePod", "type": "odometry", "port": "y",
        "options": {"offset_mm": 50}}
     ]}
  ]
}
```

Hub addresses are 1–254. Motor/encoder/I²C ports are 0–3; servo ports are 0–5.
Port spaces are distinct, but a motor also occupies its encoder port. Names must
be unique across the entire tree, including children, and cannot be `hubN`.
Pinpoint child ports are `x`/`y` and have no `module`. Their axes default to their
parent port. Children exist only under their physical parent; they do not create
separate entries in the SDK HardwareMap. A directly attached hub pod is available
through `hardwareMap.get(DcMotorEx.class, "hubPod").getCurrentPosition()`.

Python validates all options, names, and connections before committing a new
topology. The SDK synchronizes the configuration before creating controllers.
Reconfiguration intentionally resets physical state. Invalid definitions leave
the previous physical model intact.

Available `options`:

| Driver | Options and defaults |
| --- | --- |
| `motor` | `max_rpm`: 312, `ticks_per_revolution`: 537.7, `direction`: 1 (or -1) |
| `servo` | `min_pulse_us`: 500, `max_pulse_us`: 2500 |
| `odometry` | `axis`: `x`, `offset_mm`: 0, `ticks_per_mm`: 13.26291192, `direction`: 1 (or -1) |
| `pinpoint` | `ticks_per_mm`: 13.26291192, `x_offset_mm`: 0, `y_offset_mm`: 0 |

### Motors

Each motor's **Device settings** has editable maximum RPM and encoder ticks per
output-shaft revolution. The **Motor preset** dropdown fills both values from
goBILDA 5203 Yellow Jacket specifications at 12 V; either value remains editable.
Choosing a preset preserves the motor's physical direction. Available presets:

| Gear ratio | Maximum RPM | Encoder ticks/revolution |
| --- | --- | --- |
| 1:1 | 6000 | 28 |
| 3.7:1 | 1620 | 103.8 |
| 5.2:1 | 1150 | 145.1 |
| 13.7:1 | 435 | 384.5 |
| 19.2:1 | 312 | 537.7 |
| 26.9:1 | 223 | 751.8 |
| 50.9:1 | 117 | 1425.1 |
| 71.2:1 | 84 | 1993.6 |
| 99.5:1 | 60 | 2786.2 |
| 139:1 | 43 | 3895.9 |
| 188:1 | 30 | 5281.1 |

Counts are quadrature ticks after the motor's built-in gearbox. Each catalog
preset includes its manufacturer source; see, for example, the
[312 RPM specification](https://www.gobilda.com/content/spec_sheets/5203-2402-0019_spec_sheet.pdf).
The power-mode tick velocity limit is `max_rpm * ticks_per_revolution / 60`.
Velocity commands use ticks/second and are clamped to this limit.

**Physical direction → Reversed** changes the shaft's rotation relative to the
mechanism. Native motor encoder coordinates and run-to-position targets remain
consistent with the motor's own encoder. TeamCode's SDK `setDirection` still
operates independently; its reversal and physical reversal multiply. Mechanisms
read each motor's signed shaft speed, so RPM, resolution, and direction apply to
the drivetrain and its connected odometry sensors automatically. The drivetrain
also has separate wheel mounting signs and optional external gearing.

For example, a reversed 435 RPM motor uses:

```json
{"max_rpm": 435, "ticks_per_revolution": 384.5, "direction": -1}
```

These options persist in browser storage and portable hardware-map files. Apply
the hardware map while stopped to update the live model. Existing files using
`max_ticks_per_second` are converted to RPM while preserving their tick limit.

A pod's `offset_mm` describes its **physical** mount. For an x wheel it is the
leftward displacement from center; for a y wheel it is the forward displacement.
Its resolution and direction describe the physical encoder. Pinpoint options and
SDK `setOffsets`/`setEncoderResolution`/`setEncoderDirections` configure the
**estimator**. Set these to match the physical pods for accurate measurements;
a deliberate mismatch yields an incorrect estimate, as on hardware. Child
resolution does not silently change when SDK estimator settings change.

## Physical inputs and UI

The server streams nested snapshots on `/sim/drivers`. The widget registry maps
each Python `kind` to a presenter. Reactive Svelte cards update existing DOM nodes;
Pinpoint renders its own state with pod widgets nested underneath.

Use **Sensor motion input** on the **Devices** sidebar page to supply forward/left mm/s
and yaw degrees/s. Internally, `Robot.set_motion(vx, vy, angular_velocity)` uses
mm/s and radians/s, then `advance(dt)` advances the whole device tree once.
Configured mechanisms instead supply motion to their connected sensor trees
from actuator state; manual motion affects other sensors. Global actuator →
mechanism → sensor phases ensure fresh motor velocities and one sensor update
per tick. Motor and servo outputs come only from the SDK. SDK STOP, disconnect, and valid
reconfiguration clear motion and disable outputs.

## Adding a driver

1. Subclass `Driver`, `Encoder`, or `I2CDriver` in a new Python module. Implement
   `step` and `state`; add `handle_lynx` for actuator commands or `read`/`write`
   for I²C devices. Constructor options become the validated configuration keys.
2. Give the class a `display_name` and optional `option_metadata` (labels,
   bounds, choices). Constructor defaults become configuration defaults, and the
   DS builds its editor from this metadata. Register the class in `drivers/registry.py`. A new I²C subclass can use the
   existing bus router. New physical connection types also need a hub adapter in
   `Hub.attach` and command routing in `Hub.dispatch`.
3. For composite devices, declare `child_ports`, `child_connections`, and optional
   `child_defaults`. Let `Driver.advance` recurse rather than ticking children
   again in the parent's `step` method.
4. Add a presenter and register its `kind` in
   `driver-station/src/lib/model/widgets.ts`. Common encoder fields are reusable
   through `EncoderPresenter`. For custom visuals, extend `DriverCard.svelte`.
5. Add the real SDK device factory and port binding to `DesktopDeviceDrivers` if
   robot programs can access it. Rebuild with `python3 scripts/build_sdk.py` to
   refresh the packaged JVM runtime.

Snapshot fields should use explicit units. Sensors should consume shared physical
inputs or attached driver state, rather than reading browser controls directly.
