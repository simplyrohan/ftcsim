# Custom FTC SDK 12.0.0

The editable FIRST SDK and all desktop Java code live here. The Python simulator
is independent in `../sim/`. No desktop Java code lives in that server.

## Desktop build

With JDK 17+, from this directory:

```sh
cd desktop
./gradlew build
./gradlew :runtime:run           # built-in iterative and linear motor examples
# Or, in place of runtime:run:
./gradlew :biobuzz:run           # isolated BioBuzz snapshot
```

Start the Python simulator first. The SDK connects once to
`ws://localhost:9015/sim` during bootstrap and listens at
`http://localhost:1115` / `ws://localhost:1115/ds` before any OpMode is constructed.
Every hub shares that simulator socket for the SDK lifetime. Transport loss stops
the robot and requires an SDK restart; it never silently reconnects with stale
controller caches.

| Project | Purpose | Output |
| --- | --- | --- |
| `jvm/` (`:sdk`) | Upstream classes and desktop platform shims | `jvm/build/libs/ftc-sdk-jvm-12.0.0.jar` |
| `runtime/` | SDK bootstrap, hardware factory, Lynx WS client, DS HTTP/WS server | `runtime/build/libs/ftc-desktop-runtime-0.2.0.jar` |
| `examples/biobuzz/` | Copied robot code and its own Pedro/SolversLib dependencies | robot example JAR |

Core and runtime also build source JARs. There are no distribution/archive tasks.
The reusable runtime has no dependency on BioBuzz, Pedro, or a Python launcher.
See [JVM details](jvm/README.md) and [upstream patch inventory](DESKTOP-PATCHES.md).

## Android workspace

This directory remains the independent Android project. Use its own wrapper:

```sh
./gradlew :TeamCode:assembleDebug
```

Configure `local.properties` with the Android SDK location. Desktop sources and
compatibility shims are excluded from this build. Optional transports default to
null, so the original Android transport path is retained.

[EXTRACTED-SDK.md](EXTRACTED-SDK.md) records extraction and artifact hashes.
`tools/extract_sdk.py` overwrites extracted sources; reapply the documented small
patches after regeneration. The upstream README and FTC license remain in
[UPSTREAM-README.md](UPSTREAM-README.md) and [LICENSE](LICENSE).
