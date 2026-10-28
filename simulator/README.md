# FTC simulator driver

This project depends on `:sdk` and contains the pieces specific to simulation:
the loopback TCP transport, desktop hub adapter, iterative OpMode runner, Python
Lynx interceptor/model, BioBuzz snapshot and local dashboard. It produces the
separate `ftcsim-driver-0.1.0.jar`.

## Run and package

From the repository root:

```sh
./run-biobuzz.sh
./gradlew :simulator:build :simulator:installDist
./gradlew :simulator:distZip
```

The installed package is `simulator/build/install/ftcsim/`. The release archive is
`simulator/build/distributions/ftcsim-0.1.0.zip`. Both contain `bin/biobuzz`, Python,
the dashboard and mapping, copied BioBuzz code, the driver JAR, the SDK JAR and
third-party JARs. Move or extract that complete directory anywhere, then run:

```sh
./bin/biobuzz
```

It requires only a Java runtime and Python 3.9+. It does not invoke Gradle in
package mode. Optional flags include `--port 8086 --lynx-port 9016`. In a source
checkout, `--no-build` skips compilation after a successful unchanged build.

See [BioBuzz controls and assumptions](biobuzz/README.md). INIT creates the robot;
START runs Red TeleOp; STOP disables simulated outputs. Logs and runtime data go
in the simulator's `build/` directory (including in an extracted package).

## Low-level driver demonstration

Start a raw interceptor:

```sh
python3 simulator/python/lynx_server.py --port 9010
```

In another terminal, run the installed Java smoke-test launcher:

```sh
simulator/build/install/ftcsim/bin/ftcsim 9010
```

For custom physics/state, use
`python3 simulator/python/lynx_server.py --handler simulator/python/example_handler.py`.
Every outgoing command, including writes, reaches `handle(request, state)`.
Return payload bytes, return `b''` for ACK, return `None` for default dispatch,
or raise `NotImplementedError` to NACK. Payloads use the real SDK serializers.

## Protocol and boundaries

TCP binds only to `127.0.0.1`. Each frame has a four-byte big-endian length and
UTF-8 JSON, capped at 1 MiB. Request fields are `version` (1), `id`, `module`,
`command` (fully qualified Java command class), `payload` (hex SDK bytes) and
`response` (expected response class, or null). Payload numeric fields use the
Lynx little-endian layout. Replies echo `id` and set `status` to `ack`, `response`
(with hex `payload`), or `nack` (with integer `reason`). Invalid requests return
`error`. No USB datagram/interface-number framing is emulated.

Python responses are decoded by the command's actual SDK response class and
complete its original ACK/response/NACK latches. Unknown commands are intercepted
and NACKed with reason 255 unless implemented by a custom handler. The Java
transport bounds each exchange with a three-second response timeout and does not
automatically replay writes. Cached hardware reads can leave a connection idle
indefinitely; the server keeps it open. A broken transport is surfaced by the
runner, and the model disables outputs on runtime failure or heartbeat loss.

Metadata and SDK-side controller caches remain local. The intercepted boundary
is outgoing Lynx hardware commands, not every Java method. The source-level
transport hooks reside in the SDK; TCP and robot lifecycle behavior reside here.

## Verification

`./gradlew :simulator:build` runs the protocol tests and real JVM/Python tests for
motors, servos, bulk reads, BioBuzz drive/encoders, intake/lift/transfer controls,
manual diagnostics, repeated start/stop cycles and heartbeat failsafe. Packaging
checks run the installed launchers after relocation, without Gradle or access to
the source checkout. The original BioBuzz checkout is not part of any build path.
