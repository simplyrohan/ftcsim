# JVM SDK library

This project compiles the eight extracted modules plus desktop platform adapters.
Build it with `../desktop/gradlew -p ../desktop :sdk:build` from this directory.
The resulting SDK JAR and source JAR are in `build/libs/`.

SDK classes keep their upstream namespaces. Desktop-only Android adapters compile
separately against the original Android API definitions, then enter the SDK JAR.
Keep that SDK JAR before Android API-linking JARs on the runtime classpath.

`ftcsim.jvm.DesktopRuntime.initialize()` installs the headless application context
and registers standard motor/servo configuration types. That function is only the
platform bootstrap. `ftcsim.jvm.DesktopSdk` in `../runtime/` is the normal desktop
entry point: it also connects the shared simulator WebSocket, installs the optional
DS output transport, and opens the DS listener before starting an OpMode.

From `../desktop/`:

```sh
./gradlew :runtime:writeClasspath
java -Dftcsim.jvm=true -cp "$(cat ../runtime/build/classpath.txt):/path/to/robot.jar" \
  ftcsim.jvm.DesktopSdk --opmode my.robot.TeleOp --config /path/to/robot.json
```

Repeat `--opmode` to register additional classes. The host reads the real
`@TeleOp`/`@Autonomous` names and skips `@Disabled` classes; it does not scan arbitrary
classpath JARs. Robot classes must have a public no-argument constructor. The core
and runtime can also be used as Gradle library projects. Third-party robot-library
dependencies belong to the robot project.

CLI options are `--sim ws://localhost:9015/sim`, `--ds-port 1115`, `--opmode CLASS`,
and `--config FILE`. Configuration files contain a `devices` array of objects with
`name`, `type` (`motor` or `servo`), `module` (1–254), and `port` (0–3 or 0–5).
The browser may replace the configuration while no OpMode is active.

The runtime supports actual iterative and linear SDK execution through a small
package-access adapter. It does not run the Android OpModeManager, Wi-Fi discovery,
USB discovery, camera native pipelines, Blocks UI, or OnBotJava services. Transport
hooks and compatibility adapters do not make every Android API desktop-compatible.
