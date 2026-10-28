# FTC SDK JVM library

This Gradle subproject compiles the eight editable SDK modules in `sdk/` into
`ftc-sdk-jvm-12.0.0.jar`. It has no dependency on the simulator project or BioBuzz.

From the repository root:

```sh
./gradlew :sdk:build :sdk:distZip
```

The ZIP contains `lib/` (SDK plus third-party JARs), `sources/`, README files and
the original FTC license. Keep the SDK JAR first on the runtime classpath so its
desktop platform adapters take precedence over Android API-linking classes:

```text
java -cp 'lib/ftc-sdk-jvm-12.0.0.jar:lib/*:your-application.jar' your.Main
```

Initialize the runtime before using SDK facilities that need an application
context:

```java
android.app.Application context = ftcsim.jvm.DesktopRuntime.initialize();
```

The package retains upstream Java namespaces. A consumer can select an alternate
Lynx transport by implementing `com.qualcomm.hardware.lynx.LynxCommandTransport`
and calling `module.setCommandTransport(transport)`. The existing dangerous-command
guard is preserved. The TCP implementation and `DesktopHub` factory live in the
separate simulator driver package, not this SDK library.

The library compiles against Android API definitions from `android-all` and uses
small desktop adapters for logging, clocks, string resources, system properties,
and the headless application context. `DesktopRuntime` selects `ftcsim.jvm=true`
and registers the basic motor/servo configuration types. It does not start
Android services or load ARM JNI. Generated `R` symbols are for desktop linking;
they are not a compiled Android resource APK.

All SDK modules compile, but Android UI, USB discovery, camera native pipelines,
Blocks WebView execution, OnBotJava Android services, Driver Station networking
and the full Android event loop are not desktop implementations. The simulator
supplies a separate iterative lifecycle runner. LinearOpMode remains unsupported
there. The verified headless paths are the standard Lynx motor/servo controllers,
bulk reads and the copied BioBuzz TeleOp exercised by simulator integration tests.

The FTC source license is preserved in the parent directory. Dependencies retain
their own embedded notices. See `sdk/README.md` in the repository for extraction
provenance and independent Android build instructions.
