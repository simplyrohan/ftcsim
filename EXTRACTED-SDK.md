# Extracted FTC Robot Controller 12.0.0

Equivalent in purpose to https://github.com/OpenFTC/Extracted-RC: the eight
FIRST SDK Android libraries are editable local modules instead of Maven AARs.

Based on FIRST-Tech-Challenge/FtcRobotController master at
`e14c2aeb33e84d4ea21697beeea9ac49557be870` (September 12, 2026), using its
published SDK version **12.0.0**. The upstream README and license are retained.

## Build

Open this directory in Android Studio, configure an Android SDK, and use JDK 17
or newer compatible with the bundled Gradle 9.1.0 / Android Gradle Plugin 8.13.2.
The project uses Android SDK platform 30 and minSdk 24, as upstream does.

```sh
./gradlew :TeamCode:assembleDebug
```

The APK is written to `TeamCode/build/outputs/apk/debug/`.
Add robot programs under `TeamCode/src/main/java/org/firstinspires/ftc/teamcode`.
This is an Android Robot Controller workspace, not a desktop robot simulator.

## Contents and regeneration

`RobotCore`, `RobotServer`, `Hardware`, `Inspection`, `FtcCommon`, `Vision`,
`Blocks`, and `OnBotJava` contain the official Maven source JAR contents plus
resources, manifests, assets, consumer rules, bundled JARs, and ARM native
libraries from their corresponding AARs. The published FTC `classes.jar` files
are deliberately excluded so edits to the extracted Java sources take effect.
Third-party dependencies remain external artifacts.

Published BuildConfig source files are preserved, including the exact SDK
version/build timestamp; generation is disabled for the extracted modules.
Native code and third-party bundled JARs remain precompiled, because Maven
does not provide their source in these artifacts. ARM libraries support device
builds, not an x86 desktop simulator.

Run `python3 tools/extract_sdk.py` to re-download and overwrite SDK module
files. Do this in a clean checkout: it overwrites edits and is intended to
reconstruct this pinned version, not automatically migrate SDK versions.
`sdk-artifacts.sha256.json` records SHA-256 hashes for all 24 input artifacts.
The script derives external dependencies from the published POMs and supplies
the source-level project dependency graph. App dependencies in
`build.dependencies.gradle` refer to local SDK projects.

All upstream copyright notices and artifact license files are preserved.

## Validation

`:TeamCode:assembleDebug` completed successfully with JDK 21 and Android SDK 30.
All 1,270 extracted Java files compiled, duplicate-class checks passed, and a
debug APK was produced. Native symbol stripping was unavailable locally, so
Gradle packaged those official libraries unchanged. No robot hardware testing
was performed.
