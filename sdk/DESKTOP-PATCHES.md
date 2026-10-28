# Atomic upstream patch inventory

Networking and desktop orchestration live in `runtime/`, not scattered through
robot code. These are the changes to the extracted SDK source:

| File | Change |
| --- | --- |
| `Hardware/.../lynx/LynxCommandTransport.java` | Optional outgoing command interface. |
| `Hardware/.../lynx/LynxModule.java` | Setter and two send/retransmit branches after the existing dangerous-command check. Null follows original USB behavior. |
| `Hardware/.../lynx/commands/LynxRespondable.java` | Exposes expected response type and completes a response using its existing payload decoder and latch. |
| `RobotCore/.../internal/network/DriverStationTransport.java` | Optional command/data output interface. |
| `RobotCore/.../internal/network/NetworkConnectionHandler.java` | Setter plus sendCommand/sendDataToPeer transport branches. Skips creating an Android Wi-Fi lock only with `ftcsim.jvm=true`. |
| `RobotCore/.../internal/system/AppUtil.java` | Skips ARM JNI loading only with `ftcsim.jvm=true`. |

The SDK controller classes, Lynx command payload serializers, gamepad serializer,
telemetry composer, OpMode, LinearOpMode, and their thread/lifecycle methods are
unchanged. `runtime/.../DesktopLifecycle.java` is a new class in the SDK package
that calls package-private lifecycle hooks. The host supplies OpModeServices for
telemetry and stop requests and calls the SDK gamepad-update hooks.

The JSON DS receive protocol is translated by `DesktopSdk` to lifecycle calls
and HardwareMap construction. The desktop host replaces the Android event-loop
bootstrap; it does not start the normal UDP receive loop. The optional output
transport also catches SDK command sends, such as telemetry display format.
Messages without a browser implementation remain visible as protocol events.

Desktop Android compatibility classes are isolated in `jvm/src/desktop/java`.
They are never part of the Android build. The LongSparseArray shim allows the
original SDK ThreadPool bookkeeping to run without Android VMRuntime natives.

For source comparison, the initial extracted SDK is commit `38536b2` (modules
were at repository root there). `archive/native-tcp` preserves the prior desktop
architecture. SDK extraction regenerates upstream files and overwrites patches;
reapply these hooks after running the extraction script.
