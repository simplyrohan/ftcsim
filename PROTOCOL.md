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

On connect the SDK sends `role` (`controller:true` or `false`), `hello` (version,
available OpModes, configured devices), `status`, and the latest `telemetry` if
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
