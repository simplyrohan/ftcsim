# Desktop transport protocol, version 1

All messages are UTF-8 JSON in standard WebSocket text messages. WebSocket framing
replaces the former private TCP length prefix. Lynx numeric payload fields retain
the SDK's little-endian binary layout; hex is only the JSON representation.

## SDK → Python: `ws://localhost:9015/sim`

Opened once during DesktopSdk bootstrap, before any OpMode is constructed. All
modules share it. Requests use monotonically increasing IDs and replies may be
correlated independently. No automatic reconnection occurs after transport loss.

```json
{"version":1,"type":"lynx","id":1,"module":1,"command":"com.qualcomm.hardware.lynx.commands.core.LynxSetMotorConstantPowerCommand","payload":"00ff7f","response":null}
```

Before constructing SDK controllers, the runtime synchronizes the configured
physical topology on this same connection:

```json
{"version":1,"type":"configure","id":1,"devices":[{"name":"motor","type":"motor","module":1,"port":0}]}
```

Python validates the entire tree and atomically replaces it. A successful reply
is `{"type":"configure","id":1,"status":"ack","payload":""}`; invalid topology
returns `status:"error"` with a message and leaves the physical model unchanged.
Setting `validateOnly:true` validates without changing physical state; the SDK
uses this preflight before closing old hardware during reconfiguration.
Commands for unconfigured hubs are rejected. See [DRIVERS.md](DRIVERS.md) for the
built-in catalog, nested encoder inputs, and configuration options.

Writes return `{"type":"lynx","id":1,"status":"ack","payload":""}`.
Reads return `status:"response"` with hex payload, decoded by the original SDK
response class. Unsupported commands return `status:"nack",reason:255`; malformed
requests return `status:"error",message:"..."`. Expected response names are sent
by the SDK in `response`; Python dispatches by command class name, not by that
response name. Commands use actual SDK payloads, not full USB datagrams or USB
interface-number negotiation. Messages are limited to 1 MiB.

The SDK bounds sends/replies at three seconds. Transport/protocol failure closes
the shared connection and fails pending calls. Python answers WebSocket pings and
sends its own heartbeat. Disconnect disables all modeled outputs.

## Browser → SDK: `ws://localhost:1115/ds`

The SDK listens on IPv4 loopback, accepts the simulator's localhost/127.0.0.1 HTTP
origin (port matching its simulator URL), and accepts local program clients with
no Origin header. `GET http://localhost:1115` reports service/version/WS path.
Clients may also use `/` for the upgrade. All DS messages are custom JSON: this is
not Robocol framing and a physical FTC DS app cannot connect.

The SDK starts with an empty hardware map. On connect the SDK sends `role` (`controller:true` or `false`), `hello` (version,
available OpModes, configured devices and `hardwareConfigured`), `status`, and the latest `telemetry` if
available. Only the first connected client controls the robot. Others observe;
they reconnect after the controller leaves to claim control. No browser-owned
state is kept by Python.

| Input type | Fields / behavior |
| --- | --- |
| `select` | `name`: one of the advertised OpMode names; inactive only. |
| `configure` | `devices`: array of `{name,type,module,port}`; inactive only. Constructs actual SDK hardware objects. |
| `init` | Constructs selected OpMode and starts original SDK init/init_loop or LinearOpMode thread. |
| `start` | Starts the initialized OpMode through the SDK lifecycle hook. |
| `stop` | Stops user code, then sends Lynx failsafe to each hub and invalidates controller caches. |
| `gamepads` | `gamepad1` and `gamepad2` objects; omitted fields are neutral. |
| `heartbeat` | Maintains DS session liveness without changing gamepads. |

Inputs may include `id`; success/error replies echo it. Heartbeats have no reply.
Gamepad fields are four stick axes in [-1,1], two triggers in [0,1], and booleans
`a,b,x,y,dpad_up,dpad_down,dpad_left,dpad_right,left_bumper,right_bumper,`
`left_stick_button,right_stick_button,guide,start,back,touchpad`. SDK gamepad copy
and serialization maintain the normal alias/edge behavior. Browser inputs are
sent every 50 ms; the host event loop updates the SDK about every 20 ms.

After 500 ms without gamepad updates the SDK uses neutral inputs. After 1.5 s
without valid gamepad/heartbeat messages, or immediately on controller disconnect,
it stops the OpMode and disables outputs. An unresponsive OpMode causes the SDK
to close the simulator transport and refuse another INIT until restarted.

## SDK → Browser

- `status`: `state` (`idle,initialized,running,stopped,error`), selected OpMode,
  elapsed seconds, error text and simulator connectivity.
- `telemetry`: tag and data from the actual SDK TelemetryMessage. The SDK telemetry
  composer retains its configured transmission interval (default 250 ms).
- `command`: original SDK command `name` and `extra`, including telemetry display
  format commands, intercepted by the optional output transport.
- `robocol`: fallback for other SDK data objects: original message kind and base64
  serialization. The stock page has no generic decoder for these extra packets.
- `ack` / `error`: command result and optional echoed ID.

The implemented DS functions are OpMode selection, hardware configuration,
lifecycle, two gamepads, telemetry/status/errors. Android configuration XML tools,
FTC discovery/pairing, camera streaming, gamepad LED/rumble effects, and other DS
features are not implemented. The receive adapter intentionally does not start
Android UDP/Wi-Fi services. Wire transport and lifecycle adapters are replaceable
without changing robot programs.

## Browser → Python: `/sim/drivers`

A separate same-origin WebSocket streams a `drivers` catalog on connect, then
physical `state` snapshots every 100 ms. This connection does not control OpModes,
gamepads, or hardware power. Each snapshot contains `connected`, `commands`,
`motion`, and `devices`. Each device has `name`, `type`, `connection`, `port`,
`state`, and recursive `children`; root devices also contain `module`.
`GET /sim/state` exposes the same snapshot for inspection.

For explicit physical sensor inputs, this socket accepts
`{"type":"motion","vx":100,"vy":0,"angular_velocity":0.2}`.
Velocities are robot-relative forward/left mm/s and counterclockwise rad/s.
Values must be finite and bounded to ±10000 mm/s and ±100 rad/s. Omitted fields
are zero. Applying motion requires a connected SDK and returns `ack`/`error`.
Motion persists until changed or a hub failsafe, SDK STOP/disconnect, or valid
reconfiguration clears it. This input is independent of motor output until a
chassis model is implemented. Multiple browser connections see the same state.

## Browser-owned hardware configuration

`GET /sim/driver-types` returns each built-in driver's label, connection type,
port count, child connection/default rules, and constructor option metadata
(labels, types, defaults, bounds, choices). The `/ds/hardware` page builds forms
from this catalog. Navigation uses the same SDK control connection.

Hardware maps live in localStorage under
`ftcsim.hardware.v1:<encoded SDK WebSocket URL>` as `{version:1, devices:[...]}`.
They are scoped by browser origin and SDK address. Changes save locally as drafts;
Apply sends `configure` directly to the SDK. A saved map automatically restores
to an idle SDK on reconnect. Observers cannot apply maps, and applying is blocked
while an OpMode is initialized/running. SDK `hello` includes
`hardwareConfigured:false` until a DS configuration succeeds, including when an
explicitly empty map is applied. INIT requires that flag to be true. The DS also
blocks INIT when local edits differ from the SDK's applied map.

The SDK retains its live map only for its process lifetime. No map is fetched
from the setup wizard, a robot XML, or a Gradle config file.

Portable hardware-map files use
`{format:"ftcsim.hardware-map", version:1, devices:[...], notes?:"..."}`.
Import/export is entirely browser-side. Imported maps are structurally and
semantically validated before localStorage is replaced; importing does not send
`configure`. Applying still uses the same SDK message and inactive-state checks.
Optional notes stay with local/file copies and are not sent to the SDK.
