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
   each wheel's motor. A motor may be connected to only one mechanism input.
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
   shows the two child encoder names; if no sensor is selected, **Link pinpoint**
   selects the sole available Pinpoint before you apply the mechanism.
6. **Apply to simulator** while stopped. The DS saves drafts in localStorage,
   separately from the hardware map, scoped to its simulator origin and SDK
   address. Saved definitions restore after the hardware map is ready. No
   mechanism definitions are included in portable hardware-map files.

A live drivetrain widget on **Overview** displays physical pose, body
velocity, all four wheel speeds, and an orientation diagram. This physical pose
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
   `driver-station/src/lib/model/mechanism-widgets.ts`. No SDK change is needed.

`GET /sim/mechanism-types` advertises metadata. `POST /sim/mechanisms` accepts
`{"mechanisms": [...]}` and atomically applies valid bindings, returning a physical
snapshot; invalid requests return HTTP 400. Browser writes must come from the
simulator origin. `/sim/drivers` and `/sim/state` include `mechanisms`,
`mechanism_configuration`, and `mechanism_error` alongside existing driver state.
The page prevents applying while an OpMode is active; Python does not learn or
control the SDK lifecycle through this mechanism API.
