# Custom FTC SDK 12.0.0

This directory contains the extracted FTC SDK, its Android controller workspace,
and a separate JVM library build. The desktop simulator lives in `../simulator/`.

The editable modules are RobotCore, RobotServer, Hardware, Inspection, FtcCommon,
Vision, Blocks and OnBotJava. The Android project retains the upstream dependency
graph and resource/native assets. FtcRobotController and TeamCode are retained as
the Android application workspace.

## JVM package

From the repository root:

```sh
./gradlew :sdk:build :sdk:distZip
```

`jvm/build/libs/ftc-sdk-jvm-12.0.0.jar` contains compiled SDK classes and the small
desktop platform compatibility layer. The companion `-sources.jar` contains the
editable sources. `jvm/build/distributions/ftc-sdk-jvm-12.0.0.zip` bundles these with
all required third-party JARs, license notices and usage documentation.

This package does not contain the simulator's TCP driver, robot code, dashboard,
or Pedro/SolversLib dependencies. See [JVM details](jvm/README.md) for runtime
initialization and compatibility limits.

## Android workspace

Open this directory in Android Studio, or run from the repository root:

```sh
./gradlew -p sdk :TeamCode:assembleDebug
```

Configure `sdk/local.properties` with your Android SDK path. The root wrapper is
shared; the nested `sdk/settings.gradle` selects the independent Android build.

## Custom changes and provenance

- `LynxModule.setCommandTransport()` permits a synchronous command transport in
  place of USB. Its default remains the original Android USB transport.
- `LynxRespondable` exposes the expected response schema and decodes remote
  response payloads using real SDK response classes.
- AppUtil skips ARM JNI loading when `ftcsim.jvm=true` is explicitly selected.
- JVM-only Android adapters are in `jvm/src/desktop/java`; they are not compiled
  into the Android app.

[EXTRACTED-SDK.md](EXTRACTED-SDK.md) records the upstream controller revision and
artifact extraction. `sdk-artifacts.sha256.json` pins the 24 published inputs.
`tools/extract_sdk.py` regenerates the extracted modules. Regeneration overwrites
native-branch SDK edits, which must be reapplied afterward.

The original upstream controller README is preserved as
[UPSTREAM-README.md](UPSTREAM-README.md), and the FTC license is in [LICENSE](LICENSE).
