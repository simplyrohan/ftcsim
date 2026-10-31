# Mechanisms

Mechanisms connect existing physical drivers to a simulated assembly. They live
in `src/ftcsim/mechanisms`, are registered in `MECHANISMS`, and have browser widgets
in `driver-station/src/lib/model/mechanism-widgets.ts`. They are entirely internal to Python and the
DS. The Java SDK, its hardware map, Lynx transport, and TeamCode have no mechanism
API, configuration, or awareness.
Unapplied or suspended mechanisms do not prevent the SDK from initializing robot
code; only the actual hardware map is required by the DS's INIT control.

## Configure a drivetrain

1. Configure and apply the four motors on **Settings → Hardware map**. Optionally add a
   Pinpoint with its existing X and Y odometry-pod children.
2. Open **Settings → Mechanisms**, add a **Mecanum drivetrain**, and select
   each wheel's motor. Physical mechanism inputs are exclusive; read-only custom
   mechanisms may also observe those motors.
3. Set each motor's maximum RPM, ticks per output-shaft revolution, and physical
   direction on **Settings → Hardware map**, using a goBILDA preset or custom values.
   The drivetrain uses each motor's own resolution, including when motors differ.
   Set wheel diameter, front-to-rear wheel spacing, and left-to-right wheel
   spacing in mm. Defaults are examples: 96 mm wheels and 360 mm spacings.
   External gearing defaults to 1; use 2 if the motor's output shaft turns twice
   per wheel revolution. The preset already includes the motor's internal gearbox.
4. Set wheel mounting directions if needed. `1` means positive physical shaft
   velocity drives that wheel forward; `-1` reverses it. These signs multiply the
   motor's physical direction setting. SDK motor direction changes also affect
   motor velocity. Choose the combined directions to match your robot.
5. Optionally select a Pinpoint. Both child pods must be configured with the
   correct X/Y axes, physical mounting offsets, resolutions, and wiring directions.
   The hardware map alone does not connect it to a drivetrain. The sensor binding
   shows the two child encoder names. Choose the Pinpoint in Connections before
   applying the mechanism.
6. **Update simulation** while stopped. The DS saves drafts in localStorage,
   separately from the hardware map, scoped to its simulator origin and SDK
   address. Saved definitions restore after the hardware map is ready. **Save robot** exports hardware, mechanisms, and their GLB models in one
   `.fs` ZIP archive. **Load robot** validates both drafts
   together without applying them. Apply hardware first, then mechanisms.

A full-frame 3D viewer on **Overview** displays the drivebase at its physical
pose, with measured wheel speeds animating the built-in mecanum wheels.
A GLB can replace the built-in visual without changing drivetrain physics. An overlay shows
pose and expandable wheel/encoder feedback. This physical pose
is independent of the Pinpoint's estimated pose. Resetting or miscalibrating the
Pinpoint never teleports the simulated drivebase.
With a Pinpoint linked, the widget also shows each child pod's live counter,
tick velocity, and distance. These are the same driver instances shown under
Pinpoint on **Devices**, rather than separate mechanism-only encoder counters.

Definitions sent directly to Python look like:

```json
{
  "mechanisms": [{
    "name": "drivebase",
    "type": "mecanum",
    "drivers": {
      "front_left": "lf",
      "front_right": "rf",
      "rear_left": "lr",
      "rear_right": "rr",
      "pinpoint": "pinpoint"
    },
    "options": {
      "wheel_diameter_mm": 96,
      "gear_ratio": 1,
      "wheelbase_mm": 360,
      "track_width_mm": 360,
      "lateral_multiplier": 1,
      "front_left_direction": 1,
      "front_right_direction": 1,
      "rear_left_direction": 1,
      "rear_right_direction": 1
    }
  }]
}
```

Omit `pinpoint` to model a drivebase without localization sensors. Selecting it
implicitly connects its two existing child pods; mechanisms never create or
reparent drivers. Driver references, constructor options, duplicate names, and
exclusive driver use are validated before replacing the live configuration.

## Simulation pipeline

Every tick has three global phases, independent of hub address/order:

1. Advance actuator drivers, including motors and servos.
2. Advance mechanisms using the motors' measured tick velocities. Divide each
   by its own ticks/revolution, apply its physical direction, external gearing,
   wheel circumference, and mounting direction to obtain wheel speeds. Convert wheel
   velocities to robot-relative forward/left mm/s and counterclockwise rad/s,
   then integrate physical pose with a constant-body-twist SE(2) update.
3. Advance sensor trees once. A drivetrain supplies motion to its selected
   Pinpoint tree; the pods calculate physical encoder counts from mounting
   offsets, and the Pinpoint estimates pose from those counts and physical yaw.
   Its unchanged I²C registers are read by the normal SDK driver.

For X-roller mecanum wheels, with `fl`, `fr`, `rl`, `rr` in mm/s and
`k = (wheelbase + track_width) / 2`:

```text
forward = ( fl + fr + rl + rr) / 4
left    = (-fl + fr + rl - rr) / 4 * lateral_multiplier
yaw     = (-fl + fr - rl + rr) / (4 * k)
```

This uses the forward/left coordinate convention described in
[WPILib's mecanum kinematics documentation](https://docs.wpilib.org/en/stable/docs/software/kinematics-and-odometry/mecanum-drive-kinematics.html).
The implementation is an ideal kinematic model: no mass, acceleration, traction,
roller slip, collisions, or field boundaries. `lateral_multiplier` scales the
predicted strafe speed; it is not a force model.

Manual **Sensor motion input** applies only to sensors not connected to a
mechanism. Mechanism-owned sensors always receive their mechanism's calculated
motion. STOP/failsafe and SDK disconnect stop actuators and mechanism velocity,
while preserving physical pose. A successful hardware reconfiguration resets
physical state and rebinds mechanisms to the new driver instances. If required
drivers disappear, mechanisms are suspended together with a visible error;
the SDK hardware change still succeeds. Restoring a compatible hardware map
rebinds the retained definitions. Applying invalid mechanism definitions leaves
the currently running mechanisms intact.
Applying a replacement mechanism definition starts its physical pose at the
origin without resetting the referenced drivers or their sensor estimates.

## Add a mechanism

1. Subclass `Mechanism`, declare `kind`, `display_name`, `driver_slots`, and
   optional `description`/`option_metadata`. Constructor defaults become settings
   in the DS form. Driver slots name the expected driver class and whether the
   connection is required; optional child requirements describe composite devices.
2. Implement `advance(dt)` to read actuator state and update the mechanism model,
   `state()` for display, and `sensor_inputs()` to provide body motion to root
   sensor drivers. Do not advance drivers yourself. Extend `consumed_drivers`
   when a composite binding includes children, and `failsafe()` for transient
   model state. Motors/actuators must declare `phase = 'actuator'`; other drivers
   default to the sensor phase.
3. Register the class in `mechanisms/registry.py`. The generic DS editor builds
   connection selectors and setting fields from the catalog.
4. Add a Svelte component and register it in
   `driver-station/src/lib/model/mechanism-widgets.ts` for state readouts. Add a
   visual to `mechanismVisuals` in `driver-station/src/lib/scene/viewport.ts` for
   the 3D scene. No SDK change is needed.

`GET /sim/mechanism-types` advertises metadata. `POST /sim/mechanisms` accepts
`{"mechanisms": [...]}` and atomically applies valid bindings, returning a physical
snapshot; invalid requests return HTTP 400. Browser writes must come from the
simulator origin. `/sim/drivers` and `/sim/state` include `mechanisms`,
`mechanism_configuration`, and `mechanism_error` alongside existing driver state.
The page prevents applying while an OpMode is active; Python does not learn or
control the SDK lifecycle through this mechanism API.

## Custom mechanisms and uploaded models

In **Settings → Mechanisms**, click **Edit** on a mechanism’s summary row. Both
mecanum and custom mechanisms have the same **Model & origin** editor and live
3D preview. Mecanum adds **Connections** and **Drive geometry** settings; custom
mechanisms add actuator **Connections** and **Motion** mapping.

A custom mechanism reads one motor or servo, or stays static when unbound. It
never writes driver state, drives odometry, or exposes anything to the SDK. Its
read-only binding can share a motor or servo with other mechanisms. Motor input
is output-shaft revolutions (`encoder position / ticks per revolution × physical
direction`); servo input is position from 0 to 1, holding its last position when
PWM is disabled. The mapping is:

```
displacement = (input position - input at starting pose) * travel * direction
```

Rotation travel is degrees per motor revolution or per full servo range.
Translation travel is millimeters for that same input range. Choose the local X,
Y, or Z axis and optionally reverse its direction. **Test input manually** drives
only the draft preview; it sends no hardware commands.

Upload a self-contained binary glTF 2.0 (`.glb`) file of at most 20 MiB. Embed
textures and buffers. Meshopt compression is supported; export without Draco or
KTX2 compression. GLB materials, node transforms, and model origin are preserved;
the viewer does not automatically center the geometry. Authored animation clips
are not played: the mechanism moves the model as one assembly.

Model scale converts the GLB's coordinates to meters; presets cover meters,
centimeters, and millimeters. Starting position uses millimeters, with robot
axes **X forward, Y left, Z up**. Starting orientation uses roll X, pitch Y,
and yaw Z in degrees (yaw → pitch → roll composition). Motion is applied after
that starting pose, around or along its local axis; scale affects geometry only.

**Attach to origin** can reference any other mechanism, or a fixed world origin.
New custom mechanisms attach to the first drivetrain when available. A chain
such as drivetrain → turret → arm inherits every ancestor's placement and motion.
A parent's origin is its pivot after its starting pose and actuator movement;
GLB scale does not scale child offsets. Circular origin references are rejected
by validation and unavailable in the parent selector. Renaming a mechanism also
updates its child origin references. If a parent is removed, reattach its children
before exporting or applying the configuration.

GLB bytes are stored in browser IndexedDB; references and visual settings remain
in the mechanism draft in localStorage. **Save robot** produces an `.fs` file, which is a standard ZIP archive:

```
ftcsim-robot.fs
├── robot.json
└── models/
    ├── model-1.glb
    └── model-2.glb
```

`robot.json` uses format `ftcsim.robot-configuration`, version 2, and stores the
hardware, mechanism settings, and origin hierarchy. Its `assets` map connects
model IDs to relative paths such as `models/model-1.glb`; GLBs are ordinary binary
files, without base64 encoding. Shared model IDs use one file. Original upload
names remain in each mechanism's visual metadata. An archive without uploaded
models contains only `robot.json`.

The complete archive and its expanded contents are limited to 64 MiB; `robot.json`
is limited to 1 MiB and each GLB to 20 MiB. **Load robot** accepts `.fs` or `.zip`,
checks ZIP entry sizes and paths before extraction, then validates both drafts,
their origin graph, and every referenced model before replacing either draft.
Missing assets and malformed archives leave the existing robot configuration
intact. Version 1 JSON files with embedded GLBs remain loadable for migration.
A missing or unreadable asset blocks export rather than producing an
incomplete file. Physics options go only to the Python simulator; model assets,
placement, and the origin graph stay in the DS.

Visual classes implement `MechanismVisual` in `driver-station/src/lib/scene`.
The viewport composes scene transforms at each mechanism's exposed `origin`,
detaches child mechanisms before replacing a parent model, and disposes model
geometry, materials, textures, and late-loading assets when removed.

## Updating simulation and performance diagnostics

**Update simulation** sends driver bindings and motion/geometry options to
`POST /sim/mechanisms`. Python validates them and recreates mechanism instances;
this resets drivetrain pose, while existing hardware drivers and encoder counts
remain intact. Model files, model placement, and origin attachments stay in the
browser and update visually without this action. The button is disabled when the
physics configuration is already current. The request has a seven-second timeout,
not a seven-second delay; its completion message reports elapsed time.

**Settings → Performance** shows SDK and simulator round-trip latency, a smoothed
average, probe timeouts, UI scheduling delay, rendering FPS, CPU render time,
draw calls, triangle counts, geometry/texture counts, and model builds. It also
separates the last update's total request time from Python's configuration time
using the `Server-Timing` response header. CPU render timing excludes GPU work.

SDK latency piggybacks an ID on one existing gamepad frame every two seconds,
then measures its existing ACK, including SDK command-queue time. Observer tabs
use the SDK's existing HTTP service endpoint. No SDK changes are required.
Simulator latency uses a small `ping`/`pong` exchange on `/sim/drivers`, without
changing actuator state or producing an extra robot snapshot. Probes pause when
the page is hidden and reset on disconnect.

Covered, inactive-tab, and offscreen viewports stop rendering. The mechanism
preview is capped at 30 FPS and uses the same display resolution as Overview
(up to a 2× pixel ratio). Placement, origin, scale, and
motion edits update transforms on the existing model; only a different GLB or
procedural geometry dimensions rebuilds it. Hidden Overview scenes also defer
model synchronization until visible again. Model-build counters help identify
unexpected asset churn when editing large models.
