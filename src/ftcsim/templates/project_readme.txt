# TeamCodeSim

Installed by the ftcsim Python wizard. This module compiles your actual TeamCode
Java/Kotlin files against the custom desktop SDK. It does not copy or modify them.
The robot APK remains the original TeamCode Android target.

Sync Android Studio, then use FTC Robot / FTC Simulator Backend / FTC Simulator.
Or run these in separate terminals:

    ./gradlew :TeamCodeSim:startBackend
    ./gradlew runSimulator

Install ftcsim with pipx or pip before running these tasks. The backend uses the
Python executable recorded by the wizard; -PsimPython overrides it.
Open http://localhost:9015/ds after starting both tasks.

Review robot.json BEFORE INIT. Without --robot-xml the wizard creates an empty
configuration: configure motor/servo ports in the browser DS, or import your XML.
Unknown XML devices are recorded in unsupportedDevices rather than fabricated.
Pinpoint, IMU, camera, settings services, and other Android/vendor facilities need
actual desktop SDK support. Installing this target does not implement them.

Run options: -PsimOpmodes=my.robot.TeleOp,my.robot.Auto,
-PsimConfig=/path/to/robot.json, -PsimEndpoint=ws://localhost:9015/sim,
-PsimDsPort=1115. OpMode discovery is heuristic and covers top-level annotated
classes. Specify nested/generated classes explicitly with --opmode or simOpmodes.

The compiled SDK and all its JVM dependencies are linked from the installed
Python package using ftcsim.sdkDir in local.properties. --copy-sdk copies those
binaries into .ftcsim/distribution/sdk instead. Re-run ftcsim --wizard after moving
or upgrading the Python installation. The consuming project needs JDK 17+ and
Gradle, but does not compile the FTC SDK. No source checkout is needed.

Dependencies declared in TeamCode's api/implementation/compileOnly/runtimeOnly
configurations are copied as declarations into the desktop target. Project
dependencies (including FtcRobotController) are skipped; provide desktop equivalents
in extra-dependencies.gradle. Build-variant-specific dependencies, private repository
credentials, dependency constraints/resolution rules, and Android Gradle plugins
are not automatically migrated. Android AAR Java classes are extracted; their
resources/native libraries/services are not emulated by this transform.

Useful tasks: :TeamCodeSim:classes, :TeamCodeSim:verifySimulatorIsolation,
:TeamCodeSim:writeClasspath. JVM Gradle run configurations require your IDE's Gradle
support; adjust the FTC Robot module selector if your IDE names modules differently.

Generated build/adapter/README/run-configuration files are wizard-owned. Re-running
the wizard preserves user changes elsewhere in the Gradle files, and refuses to
overwrite edits to generated files unless --force is supplied. robot.json and
extra-dependencies.gradle are user-owned and preserved by default. Supplying
--robot-xml explicitly replaces robot.json with a backed-up import.

Backups are in .ftcsim/backups. Installation rolls back completed writes on failure.
The wizard does not change TeamCode sources, motor constants, localization, the
Android module build script, or the robot SDK. It never builds, deploys, or starts
the simulator automatically. Gradle/SDK/vendor runtime compatibility still needs
validation on your project after installation.
