# FTCsim

A custom FTC SDK 12.0.0 and a desktop simulator that runs a copied BioBuzz Red
TeleOp through real SDK hardware controllers and a local Python Lynx bridge.

## Layout

```text
sdk/                         Custom FTC SDK
  RobotCore/, Hardware/, …   Eight extracted, editable SDK libraries
  FtcRobotController/        Original Android controller application
  TeamCode/                  Android programming workspace
  jvm/                       Standalone JVM SDK build + desktop platform adapters
  tools/                     Reproducible extraction script and artifact checksums
simulator/                   Simulator driver (depends on the SDK project)
  src/main/java/             TCP transport, hub adapter and OpMode runner
  python/                    Lynx server, motor model and integration tests
  biobuzz/                   Isolated robot-code snapshot, mapping and dashboard
  bin/biobuzz                Launcher included in the portable distribution
run-biobuzz.sh               Source-checkout convenience launcher
```

The SDK and simulator are separate Gradle projects and produce separate JARs.
The SDK has no BioBuzz, Pedro Pathing or SolversLib dependency. The original
BioBuzz checkout is never read or modified by these builds.

## Run from source

Requires JDK 17+ and Python 3.9+ (tested with JDK 21 and Python 3.12):

```sh
./run-biobuzz.sh
```

Open **http://127.0.0.1:8085**, then INIT → START. Use WASD to drive, Q/E to turn,
Space for intake, R/F for intake lift, T for transfer, and Escape to stop.
The dashboard also provides a controller interface, shooter/turret diagnostics,
encoder/servo readouts, pose visualization and Lynx traffic.

See [the BioBuzz guide](simulator/biobuzz/README.md) for copy-only adaptations,
hardware-port assumptions, controls and simulation limitations.

## Build, verify and package

```sh
./gradlew build                 # Both projects, including integration tests
./gradlew packageAll            # SDK ZIP and runnable simulator ZIP
./gradlew :simulator:installDist # Unpacked runnable simulator
```

| Output | Location |
|---|---|
| JVM SDK JAR | `sdk/jvm/build/libs/ftc-sdk-jvm-12.0.0.jar` |
| SDK sources JAR | `sdk/jvm/build/libs/ftc-sdk-jvm-12.0.0-sources.jar` |
| SDK + dependencies ZIP | `build/distributions/ftc-sdk-jvm-12.0.0.zip` |
| Simulator driver JAR | `simulator/build/libs/ftcsim-driver-0.1.0.jar` |
| Portable simulator ZIP | `build/distributions/ftcsim-0.1.0.zip` |
| Installed simulator | `simulator/build/install/ftcsim/` |

`packageAll` collects both ZIPs into the root `build/distributions/` folder;
individual project builds also retain their ZIP under their own build folder.

The simulator distribution includes both JARs, third-party dependencies, Python
server, dashboard, BioBuzz copy and license notices. Extract it anywhere and run:

```sh
./bin/biobuzz
```

No Gradle, Android SDK, source checkout or Python packages are needed to run that
package; only Java and Python. The SDK distribution is a separate library bundle
for consumers who want the custom SDK without the simulator driver.

## SDK development

- [SDK overview](sdk/README.md)
- [JVM library/compatibility details](sdk/jvm/README.md)
- [Simulator driver/protocol](simulator/README.md)
- [Extraction provenance](sdk/EXTRACTED-SDK.md)

The Android workspace is preserved under `sdk/`. Open that folder in Android
Studio, or build it independently with `./gradlew -p sdk :TeamCode:assembleDebug`.
The root Gradle build is the desktop build and does not require an Android SDK.

This is a headless runtime with idealized hardware and motion. It is not a full
Android Robot Controller app port, a calibrated physics engine, or a validated
match/autonomous simulator. Original FTC and third-party licenses are retained.
