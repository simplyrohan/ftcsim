# FTC SDK 12.0.0 on a desktop JVM

This build compiles all eight extracted SDK modules, plus TeamCode, into ordinary
Java bytecode. It uses the Java Gradle plugin and does not require an Android SDK,
emulator, REV Control Hub, or ARM native library for the verified hardware paths.
Build with JDK 17+ (tested with JDK 21) and Python 3.9+.

## Build and run

From the repository root:

```sh
./gradlew -p native-jvm build installDist
```

`build` includes Python protocol tests and real JVM integration tests. Compilation
uses `--release 8`; running the Gradle wrapper itself requires a recent JDK.
Dependencies are downloaded on the first build. The resulting desktop library is
`native-jvm/build/libs/ftcsim-jvm.jar`; its dependencies and launcher are under
`native-jvm/build/install/ftcsim-jvm/`. Copy that entire directory to relocate it.

Start the interceptor in one terminal:

```sh
python3 native-jvm/python/lynx_server.py --port 9010 --log native-jvm/build/lynx.jsonl
```

Run the compiled JVM example in another terminal:

```sh
native-jvm/build/install/ftcsim-jvm/bin/ftcsim-jvm 9010
```

It sets motor power, reads power and encoder position through Python, and stops
the motor. For a custom simulator, load a handler:

```sh
python3 native-jvm/python/lynx_server.py --handler native-jvm/python/example_handler.py
```

That example supplies encoder position 1234 for motor 0; the JVM output reflects
that value. Every outgoing command, including writes, reaches `handle(request,
state)` before built-in dispatch. Return response payload `bytes`, return `b''`
for an ACK, return `None` to use default dispatch, or raise `NotImplementedError`
to NACK. No simulator package or third-party Python dependency is required.

## Use the ordinary SDK hardware APIs

Initialize the desktop context before loading SDK classes that need it:

```java
android.app.Application context = DesktopRuntime.initialize();
try (DesktopHub hub = new DesktopHub(9010, 1)) {
    LynxDcMotorController controller = new LynxDcMotorController(context, hub);
    DcMotorEx motor = new DcMotorImplEx(controller, 0);
    motor.setPower(0.5);
    int ticks = motor.getCurrentPosition();
    motor.setPower(0);
}
```

Desktop classes are in `ftcsim.jvm`; hardware classes retain their original FTC
packages. `ControllerSmokeTest` also demonstrates Servo and manual bulk caching.
Create more `DesktopHub` instances with different module addresses for additional
hubs. Python keeps register state separately for each address. Existing SDK
controller caches still apply; clearing a cache causes the next read to reach
Python. Metadata access and Java-side caching remain local. The intercepted
boundary is outgoing Lynx hardware commands, rather than every Java method call.

The server provides register storage for motor power, modes, enable state,
targets and PID/PIDF values; servo and PWM settings; digital I/O; ADC values;
encoders and bulk reads; basic module status, LED and failsafe commands. Encoders
remain stationary unless your handler changes `state.encoders` or returns a
custom response. This is a transport and register model, not a physics engine.
Unsupported commands, including I2C transactions and firmware operations, are
still intercepted and logged, then NACKed with reason 255 unless your handler
implements them. The bridge never forwards to USB hardware.

## Protocol and SDK changes

TCP binds only to `127.0.0.1` (default port 9010). Each frame contains a four-byte
big-endian length followed by UTF-8 JSON, capped at 1 MiB. Request fields:

```json
{"version":1,"id":1,"module":1,"command":"com.qualcomm.hardware.lynx.commands.core.LynxGetMotorEncoderPositionCommand","payload":"00","response":"com.qualcomm.hardware.lynx.commands.core.LynxGetMotorEncoderPositionResponse"}
```

Payloads are hex-encoded bytes produced by the actual SDK serializers; numeric
fields within those payloads use the Lynx little-endian layout. Replies echo
`id` and set `status` to `ack`, `response` (with hex `payload`), or `nack` (with
integer `reason`). Invalid requests return `error`. There is no wire-level Lynx
USB datagram framing or interface command-number negotiation: Java class names
identify commands. An unsupported handler is an explicit NACK, never a guessed
successful response.

`LynxModule.setCommandTransport()` selects the alternate synchronous transport.
Normal Android modules retain the original USB path when no transport is set.
The existing dangerous-command guard is retained before the transport hook.
`LynxRespondable` decodes Python payloads using the command's real response class
and completes its existing ACK/response/NACK latches. Socket calls have a 3-second
timeout; a broken connection or invalid reply closes the connection and fails
the exchange. There is no automatic replay of writes after a connection failure.

`DesktopHub` supplies a local arming/lock adapter and disables USB ping/watchdog
scheduling. `DesktopRuntime` installs a headless context and the built-in motor
and servo configuration types. Desktop-only platform adapters cover logging,
clocks, storage paths, string resources and the context used by these paths.
The explicit `ftcsim.jvm` property prevents AppUtil from loading ARM JNI. The
Android build keeps its original behavior by default.

## Scope

All SDK modules compile, but this is a **headless hardware runtime**, not a desktop
port of the Robot Controller Android app. Android UI, Blocks WebView execution,
OnBotJava's Android services, USB discovery, camera/vision native pipelines, and
Android event-loop/Driver Station services have not been ported or runtime-tested.
`android-all` supplies Android API signatures and Java implementations for linking;
it does not turn Android services or JNI methods into desktop implementations.
TeamCode is compiled, but this project does not yet provide an OpMode lifecycle
runner. The verified APIs are the low-level command path and standard motor,
servo and bulk-read controllers; additional device paths may require adapters.

Resource symbols/string lookups are generated from the extracted XML for desktop
linking; they are not an Android resource APK. `tools/extract_sdk.py` at the root
recreates upstream module files and would overwrite SDK patches on this branch;
reapply native changes after regeneration. Build output and local settings are
ignored by Git. Upstream copyright and license notices remain in their sources.
